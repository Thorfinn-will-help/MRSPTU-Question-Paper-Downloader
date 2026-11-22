import io
import os
import zipfile

import boto3
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from supabase import create_client


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

TIGRIS_ACCESS_KEY_ID = os.getenv("TIGRIS_ACCESS_KEY_ID")
TIGRIS_SECRET_ACCESS_KEY = os.getenv("TIGRIS_SECRET_ACCESS_KEY")
TIGRIS_BUCKET = os.getenv("TIGRIS_BUCKET")
TIGRIS_ENDPOINT = os.getenv("TIGRIS_ENDPOINT")


required = {
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_SERVICE_KEY": SUPABASE_SERVICE_KEY,
    "TIGRIS_ACCESS_KEY_ID": TIGRIS_ACCESS_KEY_ID,
    "TIGRIS_SECRET_ACCESS_KEY": TIGRIS_SECRET_ACCESS_KEY,
    "TIGRIS_BUCKET": TIGRIS_BUCKET,
    "TIGRIS_ENDPOINT": TIGRIS_ENDPOINT,
}

missing = [name for name, value in required.items() if not value]

if missing:
    raise RuntimeError(
        "Missing environment variables: "
        + ", ".join(missing)
    )


# ============================================================
# CLIENTS
# ============================================================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
)

tigris = boto3.client(
    "s3",
    endpoint_url=TIGRIS_ENDPOINT,
    aws_access_key_id=TIGRIS_ACCESS_KEY_ID,
    aws_secret_access_key=TIGRIS_SECRET_ACCESS_KEY,
    region_name="auto",
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="MRSPTU Question Paper Archive API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ZIP REQUEST MODEL
# ============================================================

class ZipRequest(BaseModel):
    paper_ids: list[int]


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "MRSPTU Question Paper Archive API",
    }


# ============================================================
# USAGE STATS
# ============================================================

@app.get("/stats")
def usage_stats():
    """
    Return cumulative usage statistics.

    Usage is counted as:
    - Every successful paper search request
    - Every successful individual paper download
    - Every successful ZIP download
    """

    try:

        # --------------------------------------------------------
        # TOTAL USAGE
        # --------------------------------------------------------

        total_response = (
            supabase
            .table("usage_events")
            .select("id", count="exact")
            .execute()
        )

        # --------------------------------------------------------
        # TOTAL SEARCHES
        # --------------------------------------------------------

        search_response = (
            supabase
            .table("usage_events")
            .select("id", count="exact")
            .eq("event_type", "search")
            .execute()
        )

        # --------------------------------------------------------
        # TOTAL DOWNLOADS
        # --------------------------------------------------------

        download_response = (
            supabase
            .table("usage_events")
            .select("id", count="exact")
            .eq("event_type", "download")
            .execute()
        )

        return {
            "total_usage": total_response.count or 0,
            "total_searches": search_response.count or 0,
            "total_downloads": download_response.count or 0,
        }

    except Exception as error:

        print("STATS ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve usage statistics: {error}"
        )


# ============================================================
# SEARCH PAPERS
# ============================================================

@app.get("/papers")
def search_papers(
    subject_code: str | None = Query(default=None),
    year: int | None = Query(default=None),
    paper_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
):
    try:

        query = (
            supabase
            .table("papers")
            .select(
                "id,"
                "paper_id,"
                "subject_code,"
                "year,"
                "sequence_number,"
                "file_type,"
                "file_name,"
                "storage_key"
            )
        )

        # --------------------------------------------------------
        # SUBJECT CODE
        # --------------------------------------------------------

        if subject_code:

            value = (
                subject_code
                .strip()
                .replace(" ", "")
                .replace("-", "")
                .upper()
            )

            query = query.ilike(
                "subject_code",
                value
            )

        # --------------------------------------------------------
        # YEAR
        # --------------------------------------------------------

        if year:
            query = query.eq("year", year)

        # --------------------------------------------------------
        # PAPER ID
        # --------------------------------------------------------

        if paper_id:

            value = paper_id.strip()

            query = query.ilike(
                "paper_id",
                value
            )

        # --------------------------------------------------------
        # EXECUTE SEARCH
        # --------------------------------------------------------

        response = (
            query
            .order("year", desc=True)
            .order("subject_code")
            .order("sequence_number")
            .limit(limit)
            .execute()
        )

        papers = response.data or []

        # --------------------------------------------------------
        # RECORD SEARCH
        # --------------------------------------------------------

        # Statistics must NEVER break an otherwise successful search.
        try:

            supabase.table("usage_events").insert({
                "event_type": "search"
            }).execute()

        except Exception as error:

            print(
                "SEARCH STATS ERROR:",
                repr(error)
            )

        # --------------------------------------------------------
        # RETURN RESULTS
        # --------------------------------------------------------

        return {
            "count": len(papers),
            "papers": papers,
        }

    except Exception as error:

        print(
            "SEARCH ERROR:",
            repr(error)
        )

        raise HTTPException(
            status_code=500,
            detail=f"Database search failed: {error}"
        )


# ============================================================
# GET ONE PAPER
# ============================================================

@app.get("/papers/{paper_id_number}")
def get_paper(paper_id_number: int):

    response = (
        supabase
        .table("papers")
        .select("*")
        .eq("id", paper_id_number)
        .maybe_single()
        .execute()
    )

    if response is None or not response.data:

        raise HTTPException(
            status_code=404,
            detail="Paper not found."
        )

    return response.data


# ============================================================
# DOWNLOAD ONE PAPER
# ============================================================

@app.get("/papers/{paper_id_number}/download")
def download_paper(paper_id_number: int):

    # --------------------------------------------------------
    # GET PAPER METADATA
    # --------------------------------------------------------

    response = (
        supabase
        .table("papers")
        .select("*")
        .eq("id", paper_id_number)
        .maybe_single()
        .execute()
    )

    if response is None or not response.data:

        raise HTTPException(
            status_code=404,
            detail="Paper not found."
        )

    paper = response.data
    storage_key = paper["storage_key"]

    # --------------------------------------------------------
    # GET FILE FROM TIGRIS
    # --------------------------------------------------------

    try:

        obj = tigris.get_object(
            Bucket=TIGRIS_BUCKET,
            Key=storage_key,
        )

    except Exception as error:

        raise HTTPException(
            status_code=404,
            detail=f"File not found in storage: {error}",
        )

    # --------------------------------------------------------
    # RECORD SUCCESSFUL DOWNLOAD
    # --------------------------------------------------------

    # Only count the download if the file was successfully
    # retrieved from Tigris.

    try:

        supabase.table("usage_events").insert({
            "event_type": "download"
        }).execute()

    except Exception as error:

        # Never break a valid download because statistics failed.
        print(
            "DOWNLOAD STATS ERROR:",
            repr(error)
        )

    # --------------------------------------------------------
    # FILE TYPE
    # --------------------------------------------------------

    file_type = paper["file_type"].lower()

    if file_type == "pdf":

        content_type = "application/pdf"

    elif file_type == "docx":

        content_type = (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )

    else:

        content_type = "application/octet-stream"

    # --------------------------------------------------------
    # STREAM FILE
    # --------------------------------------------------------

    return StreamingResponse(
        obj["Body"].iter_chunks(
            chunk_size=1024 * 1024
        ),
        media_type=content_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{paper["file_name"]}"'
            )
        },
    )


# ============================================================
# DOWNLOAD MULTIPLE PAPERS AS ZIP
# ============================================================

@app.post("/papers/download-zip")
def download_zip(request: ZipRequest):

    # --------------------------------------------------------
    # VALIDATE REQUEST
    # --------------------------------------------------------

    if not request.paper_ids:

        raise HTTPException(
            status_code=400,
            detail="No papers selected."
        )

    # Remove duplicate IDs while preserving order
    paper_ids = list(
        dict.fromkeys(request.paper_ids)
    )

    # --------------------------------------------------------
    # GET PAPER METADATA
    # --------------------------------------------------------

    response = (
        supabase
        .table("papers")
        .select("*")
        .in_("id", paper_ids)
        .execute()
    )

    papers = response.data or []

    if not papers:

        raise HTTPException(
            status_code=404,
            detail="No papers found."
        )

    # --------------------------------------------------------
    # CREATE ZIP IN MEMORY
    # --------------------------------------------------------

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(
        zip_buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as zip_file:

        used_names = set()

        for paper in papers:

            storage_key = paper["storage_key"]
            original_name = paper["file_name"]

            # ------------------------------------------------
            # GET FILE FROM TIGRIS
            # ------------------------------------------------

            try:

                obj = tigris.get_object(
                    Bucket=TIGRIS_BUCKET,
                    Key=storage_key,
                )

                file_data = obj["Body"].read()

            except Exception as error:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Could not retrieve "
                        f"{original_name}: {error}"
                    ),
                )

            # ------------------------------------------------
            # PREVENT DUPLICATE ZIP FILENAMES
            # ------------------------------------------------

            zip_name = original_name

            if zip_name in used_names:

                base, extension = os.path.splitext(
                    original_name
                )

                counter = 2

                while (
                    f"{base}_{counter}{extension}"
                    in used_names
                ):
                    counter += 1

                zip_name = (
                    f"{base}_{counter}{extension}"
                )

            used_names.add(zip_name)

            # ------------------------------------------------
            # ADD FILE TO ZIP
            # ------------------------------------------------

            zip_file.writestr(
                zip_name,
                file_data,
            )

    # --------------------------------------------------------
    # RESET BUFFER
    # --------------------------------------------------------

    zip_buffer.seek(0)

    # --------------------------------------------------------
    # RECORD SUCCESSFUL ZIP DOWNLOAD
    # --------------------------------------------------------

    try:

        supabase.table("usage_events").insert({
            "event_type": "download"
        }).execute()

    except Exception as error:

        # Never break a valid ZIP download because
        # statistics recording failed.
        print(
            "ZIP DOWNLOAD STATS ERROR:",
            repr(error)
        )

    # --------------------------------------------------------
    # RETURN ZIP
    # --------------------------------------------------------

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                'attachment; '
                'filename="MRSPTU_Question_Papers.zip"'
            )
        },
    )
