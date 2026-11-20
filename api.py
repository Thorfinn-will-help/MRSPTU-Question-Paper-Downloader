from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from downloader import download_papers

import os
import uuid
import threading


app = FastAPI(
    title="MRSPTU Question Paper Downloader"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# JOB STORAGE
# ============================================================

jobs = {}


class DownloadRequest(BaseModel):
    subjects: list[str]


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "MRSPTU Question Paper Downloader API"
    }


# ============================================================
# START DOWNLOAD
# ============================================================

@app.post("/download")
def start_download(request: DownloadRequest):

    subjects = []

    for subject in request.subjects:

        subject = subject.strip().upper()

        if subject and subject not in subjects:
            subjects.append(subject)

    if not subjects:
        raise HTTPException(
            status_code=400,
            detail="No subject codes provided."
        )

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "starting",
        "message": "Starting downloader...",
        "progress": 0,
        "eta": "--:--",
        "zip_path": None,
        "error": None,
    }

    thread = threading.Thread(
        target=run_download,
        args=(job_id, subjects),
        daemon=True
    )

    thread.start()

    return {
        "job_id": job_id
    }


# ============================================================
# DOWNLOAD WORKER
# ============================================================

def run_download(job_id, subjects):

    def status_callback(message):

        progress = 0

        # Example:
        # Downloaded 6/10 | Successful: 6 | Failed: 0 | ETA: 00:12

        if message.startswith("Downloaded "):

            try:
                part = message.split("|")[0]
                numbers = part.replace(
                    "Downloaded ", ""
                )

                completed, total = numbers.split("/")

                completed = int(completed)
                total = int(total)

                if total > 0:
                    progress = int(
                        (completed / total) * 100
                    )

            except Exception:
                pass

        elif message.startswith("ZIP ready:"):

            progress = 100

        jobs[job_id]["message"] = message
        jobs[job_id]["progress"] = progress

        # Extract ETA
        if "ETA:" in message:

            try:
                eta = message.split("ETA:")[-1].strip()
                jobs[job_id]["eta"] = eta
            except Exception:
                pass

    try:

        jobs[job_id]["status"] = "running"

        zip_path = download_papers(
            subjects,
            status_callback=status_callback
        )

        if not zip_path or not os.path.exists(zip_path):

            raise Exception(
                "No ZIP file was created."
            )

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = (
            "Download completed successfully."
        )
        jobs[job_id]["eta"] = "00:00"
        jobs[job_id]["zip_path"] = zip_path

    except Exception as error:

        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(error)
        jobs[job_id]["message"] = (
            f"Error: {error}"
        )


# ============================================================
# CHECK PROGRESS
# ============================================================

@app.get("/status/{job_id}")
def get_status(job_id):

    if job_id not in jobs:

        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )

    job = jobs[job_id]

    return {
        "status": job["status"],
        "message": job["message"],
        "progress": job["progress"],
        "eta": job["eta"],
        "error": job["error"],
    }


# ============================================================
# GET ZIP
# ============================================================

@app.get("/download/{job_id}")
def get_download(job_id):

    if job_id not in jobs:

        raise HTTPException(
            status_code=404,
            detail="Job not found."
        )

    job = jobs[job_id]

    if job["status"] != "completed":

        raise HTTPException(
            status_code=400,
            detail="Download is not ready yet."
        )

    zip_path = job["zip_path"]

    if not zip_path or not os.path.exists(zip_path):

        raise HTTPException(
            status_code=404,
            detail="ZIP file no longer exists."
        )

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="MRSPTU_Question_Papers.zip"
    )