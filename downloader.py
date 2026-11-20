import re
import time
import requests
import zipfile
import tempfile
from pathlib import Path
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

SITES = {
    "2024": "https://library.mrsptu.ac.in/question-paper-2024/",
    "2023": "https://library.mrsptu.ac.in/question-paper-2023/",
    "2022": "https://library.mrsptu.ac.in/question-papers/",
}

REQUEST_TIMEOUT = 30
MAX_WORKERS = 6

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120 Safari/537.36"
    )
}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def normalize_code(code):
    """
    Remove spaces and hyphens and convert to uppercase.

    Examples:
        BMECS1501
        BMECS 1501
        BMECS-1501

    All become:
        BMECS1501
    """
    return re.sub(r"[\s\-]+", "", code).upper()


def safe_file_name(name):
    """Make a filename safe for Windows/Linux."""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()


def format_time(seconds):
    """Convert seconds into HH:MM:SS or MM:SS."""
    if seconds is None or seconds < 0:
        return "--:--"

    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"


def calculate_eta(start_time, completed, total):
    """Estimate remaining time based on current progress."""
    if completed <= 0 or total <= 0:
        return None

    elapsed = time.time() - start_time
    average_time = elapsed / completed
    remaining_items = total - completed

    return average_time * remaining_items


# ============================================================
# MRSPTU SEARCH
# ============================================================

def subject_matches(row, subject):
    """Check whether a table row contains the requested subject code."""
    target = normalize_code(subject)

    cells = row.find_all(["td", "th"])

    for cell in cells:
        text = cell.get_text(" ", strip=True)

        if normalize_code(text) == target:
            return True

    return False


def find_papers(subject, site_url):
    """
    Find all question-paper links for a subject on one MRSPTU page.
    """

    try:
        response = requests.get(
            site_url,
            timeout=REQUEST_TIMEOUT,
            headers=HEADERS,
        )

        response.raise_for_status()

    except requests.RequestException as error:
        print(f"  [ERROR] Could not access {site_url}")
        print(f"          {error}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    papers = []

    for row in soup.find_all("tr"):

        if not subject_matches(row, subject):
            continue

        for link in row.find_all("a", href=True):

            href = link["href"].strip()
            text = link.get_text(" ", strip=True).lower()

            full_url = urljoin(site_url, href)

            is_document = (
                "download" in text
                or "docs.google.com" in full_url
                or "drive.google.com" in full_url
                or ".pdf" in full_url.lower()
                or ".doc" in full_url.lower()
                or ".docx" in full_url.lower()
            )

            if is_document and full_url not in papers:
                papers.append(full_url)

    return papers


# ============================================================
# RESPONSE CHECKING
# ============================================================

def is_html_response(response):
    """
    Detect whether a request returned an HTML page instead
    of the expected document.
    """

    content_type = response.headers.get(
        "Content-Type",
        ""
    ).lower()

    body_start = response.content[:500].lstrip().lower()

    return (
        "text/html" in content_type
        or body_start.startswith(b"<!doctype html")
        or body_start.startswith(b"<html")
    )


# ============================================================
# DIRECT PDF DOWNLOAD
# ============================================================

def download_direct_pdf(url, output_file):

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers=HEADERS,
        )

        response.raise_for_status()

        if is_html_response(response):
            print("    [SKIPPED] HTML response")
            return False

        data = response.content

        if not data.startswith(b"%PDF"):
            print("    [SKIPPED] Response is not a PDF")
            return False

        output_file.write_bytes(data)

        return True

    except Exception as error:
        print(f"    [FAILED] {error}")
        return False


# ============================================================
# GOOGLE DOCS
# ============================================================

def get_google_doc_id(url):

    match = re.search(
        r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)",
        url
    )

    return match.group(1) if match else None


def get_google_drive_id(url):

    patterns = [
        r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)",
        r"drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)",
        r"(?:^|&)id=([a-zA-Z0-9_-]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            url,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    return None


def download_google_doc_as_docx(url, output_file):

    document_id = get_google_doc_id(url)

    if not document_id:
        print("    [FAILED] Could not extract Google Docs ID")
        return False

    export_url = (
        f"https://docs.google.com/document/d/"
        f"{document_id}/export?format=docx"
    )

    try:

        response = requests.get(
            export_url,
            timeout=REQUEST_TIMEOUT,
            headers=HEADERS,
            allow_redirects=True,
        )

        response.raise_for_status()

        if is_html_response(response):
            print("    [FAILED] Google Docs returned HTML")
            return False

        data = response.content

        # DOCX is a ZIP container and normally starts with PK.
        if not data.startswith(b"PK"):
            print("    [FAILED] Response is not a DOCX")
            return False

        output_file.write_bytes(data)

        return True

    except Exception as error:
        print(f"    [FAILED] Google Docs export: {error}")
        return False


# ============================================================
# GOOGLE DRIVE
# ============================================================

def download_google_drive(url, output_file):
    """
    Download a Google Drive file without using a browser.
    """

    file_id = get_google_drive_id(url)

    if not file_id:
        print("    [SKIPPED] Could not extract Google Drive file ID")
        return False

    try:

        response = requests.get(
            f"https://drive.google.com/uc?export=download&id={file_id}",
            timeout=REQUEST_TIMEOUT,
            headers=HEADERS,
            allow_redirects=True,
        )

        response.raise_for_status()

        if is_html_response(response):
            print("    [SKIPPED] Google Drive returned HTML")
            return False

        if not response.content:
            return False

        output_file.write_bytes(response.content)

        return True

    except Exception as error:
        print(f"    [FAILED] {error}")
        return False


# ============================================================
# PROCESS ONE PAPER
# ============================================================

def process_paper(url, output_file):

    lower_url = url.lower()

    print(f"    Source: {url}")

    # Google Docs
    if "docs.google.com/document" in lower_url:
        return download_google_doc_as_docx(
            url,
            output_file
        )

    # Google Drive
    if "drive.google.com" in lower_url:
        return download_google_drive(
            url,
            output_file
        )

    # Direct PDF
    if ".pdf" in lower_url:
        return download_direct_pdf(
            url,
            output_file
        )

    # DOC / DOCX
    if ".docx" in lower_url or ".doc" in lower_url:

        try:

            response = requests.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers=HEADERS,
            )

            response.raise_for_status()

            if is_html_response(response):
                print("    [SKIPPED] HTML response")
                return False

            output_file.write_bytes(
                response.content
            )

            return True

        except Exception as error:
            print(f"    [FAILED] {error}")
            return False

    print("    [SKIPPED] Unknown/HTML link")

    return False


# ============================================================
# OUTPUT FILE NAME
# ============================================================

def get_output_filename(
    folder,
    subject,
    year,
    index,
    url
):
    """
    Generate filenames such as:

        BMECS1501_2024.pdf
        BMECS1501_2024(1).pdf
        BMECS1501_2024(2).pdf
    """

    subject = safe_file_name(subject)

    lower_url = url.lower()

    # Google Docs exports as DOCX.
    extension = (
        ".docx"
        if "docs.google.com/document" in lower_url
        else ".pdf"
    )

    if (
        ".docx" in lower_url
        and "docs.google.com/document" not in lower_url
    ):
        extension = ".docx"

    elif (
        ".doc" in lower_url
        and ".docx" not in lower_url
        and "docs.google.com/document" not in lower_url
    ):
        extension = ".doc"

    suffix = "" if index == 0 else f"({index})"

    return (
        folder
        / f"{subject}_{year}{suffix}{extension}"
    )


# ============================================================
# DOWNLOAD EVERYTHING
# ============================================================

def download_papers(subjects, status_callback=None):
    """
    Download all question papers for the supplied subjects.

    Parameters
    ----------
    subjects : list
        List of MRSPTU subject codes.

    status_callback : function, optional
        Function receiving one string:

            status_callback("Fetching subject 1/5: BMECS1501")

        This is used by the Gradio web interface to show
        live progress.

    Returns
    -------
    str
        Path to the generated ZIP file.
    """

    total_start_time = time.time()

    total_subjects = len(subjects)

    # --------------------------------------------------------
    # STATUS HELPER
    # --------------------------------------------------------

    def status(message):
        """
        Print to terminal and optionally send the message
        to the web interface.
        """

        print(message)

        if status_callback:
            try:
                status_callback(message)
            except Exception:
                # Never allow a UI callback failure to break
                # the actual downloader.
                pass

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("MRSPTU QUESTION PAPER DOWNLOADER")
    print("=" * 60)

    print(f"Subjects: {total_subjects}")
    print(f"Parallel downloads: {MAX_WORKERS}")

    # --------------------------------------------------------
    # TEMPORARY DIRECTORY
    # --------------------------------------------------------

    temp_directory = tempfile.mkdtemp(
        prefix="mrsptu_papers_"
    )

    base_folder = Path(temp_directory)

    # --------------------------------------------------------
    # SEARCH FOR PAPERS
    # --------------------------------------------------------

    status("Searching MRSPTU question-paper database...")

    subject_papers = {}

    total_files = 0

    for subject_index, subject in enumerate(
        subjects,
        start=1
    ):

        status(
            f"Fetching subject "
            f"{subject_index}/{total_subjects}: "
            f"{subject}"
        )

        papers_for_subject = []

        seen = set()

        # Search order:
        # 2024 -> 2023 -> 2022

        for year, site_url in SITES.items():

            for paper in find_papers(
                subject,
                site_url
            ):

                if paper not in seen:

                    seen.add(paper)

                    papers_for_subject.append(
                        (year, paper)
                    )

        subject_papers[subject] = (
            papers_for_subject
        )

        total_files += len(
            papers_for_subject
        )

        status(
            f"Found "
            f"{len(papers_for_subject)} "
            f"question paper(s) for "
            f"{subject}"
        )

    # --------------------------------------------------------
    # TOTAL PAPERS FOUND
    # --------------------------------------------------------

    status(
        f"Found {total_files} question paper(s) "
        f"in total"
    )

    if total_files == 0:
        raise Exception(
            "No question papers were found."
        )

    # --------------------------------------------------------
    # BUILD DOWNLOAD TASKS
    # --------------------------------------------------------

    tasks = []

    for subject in subjects:

        subject_folder = (
            base_folder
            / safe_file_name(subject)
        )

        subject_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        year_counters = {}

        for year, paper_url in subject_papers[
            subject
        ]:

            index = year_counters.get(
                year,
                0
            )

            year_counters[year] = index + 1

            output_file = get_output_filename(
                subject_folder,
                subject,
                year,
                index,
                paper_url,
            )

            tasks.append(
                (
                    subject,
                    year,
                    paper_url,
                    output_file,
                )
            )

    # --------------------------------------------------------
    # START DOWNLOADS
    # --------------------------------------------------------

    status(
        f"Downloading {total_files} "
        f"question paper(s)..."
    )

    completed = 0
    successful = 0
    failed = 0

    def worker(task):

        subject, year, url, output_file = task

        print(
            f"\n[{subject} | {year}] "
            f"{output_file.name}"
        )

        result = process_paper(
            url,
            output_file
        )

        return result, output_file

    # --------------------------------------------------------
    # PARALLEL DOWNLOAD
    # --------------------------------------------------------

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        futures = [
            executor.submit(
                worker,
                task
            )
            for task in tasks
        ]

        for future in as_completed(
            futures
        ):

            success, output_file = (
                future.result()
            )

            completed += 1

            if success:

                successful += 1

                print(
                    f"    [OK] "
                    f"{output_file.name}"
                )

            else:

                failed += 1

                print(
                    f"    [FAILED] "
                    f"{output_file.name}"
                )

            # --------------------------------------------
            # ETA
            # --------------------------------------------

            elapsed = (
                time.time()
                - total_start_time
            )

            eta = calculate_eta(
                total_start_time,
                completed,
                total_files,
            )

            status(
                f"Downloaded "
                f"{completed}/{total_files} | "
                f"Successful: {successful} | "
                f"Failed: {failed} | "
                f"ETA: {format_time(eta)}"
            )

    # --------------------------------------------------------
    # CREATE ZIP
    # --------------------------------------------------------

    status(
        f"Creating ZIP with "
        f"{successful} question paper(s)..."
    )

    zip_path = (
        Path(tempfile.gettempdir())
        / (
            "MRSPTU_Question_Papers_"
            f"{int(time.time())}.zip"
        )
    )

    print("\n" + "=" * 60)
    print("CREATING ZIP")
    print("=" * 60)

    with zipfile.ZipFile(
        zip_path,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zip_file:

        for file in base_folder.rglob("*"):

            if file.is_file():

                zip_file.write(
                    file,
                    file.relative_to(
                        base_folder
                    ),
                )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    total_elapsed = (
        time.time()
        - total_start_time
    )

    print("\n" + "=" * 60)
    print("DOWNLOAD COMPLETED")
    print("=" * 60)

    print(f"Subjects: {total_subjects}")
    print(f"Files downloaded: {successful}")
    print(f"Files failed/skipped: {failed}")
    print(
        f"Total time: "
        f"{format_time(total_elapsed)}"
    )

    status(
        f"ZIP ready: "
        f"{successful} question paper(s) "
        f"in the ZIP | "
        f"Time: {format_time(total_elapsed)}"
    )

    return str(zip_path)