# MRSPTU Question Paper Archive

A searchable, verified archive of MRSPTU question papers.

The project collects question papers from official MRSPTU sources, verifies their metadata, stores the files in cloud storage, and provides a web interface for searching and downloading papers.

> **Archive status:** 5,676 / 5,967 expected papers currently archived  
> **Coverage:** 95.1%  
> **Years currently archived:** 2022, 2023, 2024

---

## Features

- Search question papers by **Subject Code**
- Search question papers by **Paper ID**
- Search across multiple years
- Results grouped by subject and year
- Download individual papers
- Download multiple papers as a ZIP
- Supports PDF and DOCX question papers
- Verified metadata and canonical filenames
- Persistent question-paper archive
- Cloud-based file storage
- Database-backed metadata
- GitHub Pages frontend
- FastAPI backend
- Mobile-friendly interface
- Dark mode

---

## Architecture

```text
                 Official MRSPTU Sources
                          │
                          ▼
                  Download All Papers
                          │
                          ▼
                   Local Archive
                          │
                          ▼
                 One-Time Verification
                          │
                          ▼
                  Verified Metadata
                     │          │
                     │          │
                     ▼          ▼
                 Supabase     Tigris
                 Database     Storage
                     │          │
                     └────┬─────┘
                          │
                          ▼
                    FastAPI Backend
                          │
                          ▼
                 GitHub Pages Frontend
```

The archive is designed around a **one-time collection and verification model**.

The system does not need to repeatedly scrape MRSPTU every time a student searches for a paper.

---

# Project Structure

```text
MRSPTU-Question-Paper-Downloader/
│
├── .github/
│
├── Frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
│
├── api.py
├── downloader.py
├── LICENSE
├── readme.md
└── requirement.txt
```

---

# Archive Structure

The local archive is maintained separately from the public application.

```text
MRSPTU_ARCHIVE/
│
├── 2022/
├── 2023/
├── 2024/
│
├── archive.log
├── archive_state.json
├── blocked_urls.txt
└── inventory.csv
```

The archive currently contains:

| Year | Papers |
|------|-------:|
| 2022 | 1,604 |
| 2023 | 784 |
| 2024 | 3,288 |
| **Total** | **5,676** |

Expected official paper count:

| Year | Expected |
|------|---------:|
| 2022 | 1,622 |
| 2023 | 1,050 |
| 2024 | 3,295 |
| **Total** | **5,967** |

Current archive coverage:

**5,676 / 5,967 = 95.1%**

The remaining papers can be added later without changing the overall architecture.

---

# Verification System

Downloaded filenames cannot always be trusted.

The verification system therefore uses the **document contents** as the authoritative source for metadata.

## Word Documents

For `.docx` files, the verifier checks:

- Paragraphs
- Tables
- Headers
- Footers
- The first portion of the document

The verifier attempts to identify:

- Paper ID
- Subject Code

If the metadata cannot be identified confidently, the document is placed in the verification queue rather than being guessed.

`.doc` files are not automatically processed by `python-docx` and require separate handling.

---

## PDF Documents

For PDFs, verification uses:

- The first page
- The upper portion of the page
- Embedded PDF text when available
- OCR when embedded text is unavailable

The **Subject Code is mandatory**.

The **Paper ID is optional** for PDFs.

Therefore:

```text
Paper ID + Subject Code
        ↓
Verified
        ↓
Filename contains both
```

or:

```text
Subject Code only
        ↓
Verified
        ↓
Filename contains Subject Code
```

If the Subject Code cannot be identified:

```text
Unverified
        ↓
Manual review queue
```

The system deliberately avoids guessing metadata.

---

# Canonical File Naming

Verified files follow a consistent naming scheme.

### With Paper ID

```text
PAPER_ID_SUBJECT_CODE_YEAR_N.ext
```

Example:

```text
23440104_BACSD1-111_2024_2.docx
```

### Without Paper ID

```text
SUBJECT_CODE_YEAR_N.pdf
```

Example:

```text
BME-101_2024_1.pdf
```

`N` is the sequence number for files sharing the same metadata combination.

For example:

```text
23440104_BACSD1-111_2024_1.docx
23440104_BACSD1-111_2024_2.docx
```

Existing correctly named files retain their existing sequence number.

---

# Database

Question-paper metadata is stored in **Supabase PostgreSQL**.

The main table is:

```text
papers
```

with the following fields:

| Field | Description |
|---|---|
| `id` | Internal database ID |
| `paper_id` | MRSPTU Paper ID, when available |
| `subject_code` | Subject code |
| `year` | Examination year |
| `sequence_number` | File sequence number |
| `file_type` | PDF or DOCX |
| `file_name` | Canonical filename |
| `storage_key` | Tigris storage key |
| `created_at` | Database insertion timestamp |

Indexes are maintained for:

- Subject Code
- Year
- Paper ID

---

# File Storage

Actual question-paper files are stored in **Tigris object storage**.

Supabase stores metadata only.

```text
Supabase
    │
    ├── Subject Code
    ├── Paper ID
    ├── Year
    ├── Filename
    └── Storage Key

Tigris
    │
    └── Actual PDF / DOCX file
```

This separation keeps the database lightweight and allows the application to retrieve files only when required.

---

# Backend

The backend is built with **FastAPI**.

Main API functionality includes:

```text
GET /
```

Returns API status.

```text
GET /papers
```

Search question papers.

Supported parameters:

```text
subject_code
year
paper_id
limit
```

Example:

```text
/papers?subject_code=BACSD1-111
```

Example:

```text
/papers?paper_id=23440104
```

Individual paper metadata:

```text
GET /papers/{id}
```

Download an individual paper:

```text
GET /papers/{id}/download
```

---

# Frontend

The frontend is a static web application consisting of:

```text
HTML
CSS
JavaScript
```

It is hosted using **GitHub Pages**.

Current frontend:

```text
https://thorfinn-will-help.github.io/MRSPTU-Question-Paper-Downloader/
```

The frontend communicates with the FastAPI backend through HTTP requests.

---

# Local Development

## 1. Clone the repository

```bash
git clone https://github.com/Thorfinn-will-help/MRSPTU-Question-Paper-Downloader.git
```

Enter the repository:

```bash
cd MRSPTU-Question-Paper-Downloader
```

---

## 2. Install dependencies

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirement.txt
```

---

## 3. Configure environment variables

Create a local environment file containing:

```text
SUPABASE_URL=
SUPABASE_SERVICE_KEY=

TIGRIS_ACCESS_KEY_ID=
TIGRIS_SECRET_ACCESS_KEY=
TIGRIS_BUCKET=
TIGRIS_ENDPOINT=
```

### Important

Never commit these credentials.

The following files should remain private:

```text
.env
supabase.env
tigris.env
```

They are included in `.gitignore`.

The Supabase service key and Tigris secret key must **never** be placed in frontend JavaScript.

---

# Running the Backend

From the repository root:

```bash
uvicorn api:app --reload
```

The API will normally be available at:

```text
http://127.0.0.1:8000
```

API documentation is automatically available through FastAPI at:

```text
http://127.0.0.1:8000/docs
```

---

# Running the Frontend Locally

Open another terminal:

```powershell
cd Frontend
```

Start a local HTTP server:

```powershell
python -m http.server 5500
```

Open:

```text
http://127.0.0.1:5500
```

The frontend's `API_URL` should point to the local FastAPI server during development:

```javascript
const API_URL = "http://127.0.0.1:8000";
```

---

# Deployment

The intended production architecture is:

```text
GitHub Pages
      │
      │ HTTPS
      ▼
FastAPI on Render
      │
      ├──────────────► Supabase
      │                 Metadata
      │
      └──────────────► Tigris
                        File Storage
```

## Frontend

Hosted on:

```text
GitHub Pages
```

## Backend

The FastAPI backend can be deployed as a web service on:

```text
Render
```

Recommended start command:

```bash
uvicorn api:app --host 0.0.0.0 --port $PORT
```

Build command:

```bash
pip install -r requirement.txt
```

Production environment variables must be configured through the hosting provider.

---

# Security

The project follows a basic separation of public and private components.

### Public

```text
GitHub Pages
Frontend JavaScript
Search interface
```

### Private

```text
Supabase Service Key
Tigris Access Key
Tigris Secret Key
Database credentials
```

The frontend must never contain:

```text
SUPABASE_SERVICE_KEY
TIGRIS_SECRET_ACCESS_KEY
```

Only the backend should have access to these credentials.

---

# Current Limitations

The archive is currently incomplete.

```text
Expected: 5,967
Archived: 5,676
Missing:    291
Coverage: 95.1%
```

The missing papers can be recovered and inserted into the existing archive later.

Other limitations include:

- Some PDFs do not contain a Paper ID.
- Some documents require OCR.
- Some Word documents may require manual verification.
- Legacy `.doc` files require separate processing.
- The current archive covers 2022-2024.
- Metadata quality depends on what is actually present in the official documents.

The system intentionally prefers **unverified** over incorrectly verified.

---

# Design Philosophy

The project follows four principles:

### 1. Content over filename

A filename is not considered authoritative metadata.

The actual document content is checked whenever possible.

### 2. Verify once, serve many times

The expensive work happens during archive creation.

Students should not have to wait for a scraper every time they need a question paper.

### 3. No guessing

If metadata cannot be confidently identified, the document goes into a verification queue.

Incorrect metadata is worse than missing metadata.

### 4. Separate metadata from files

Supabase handles searchable metadata.

Tigris handles the actual files.

FastAPI connects the two.

---

# Technology Stack

| Component | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, FastAPI |
| Database | Supabase PostgreSQL |
| Object Storage | Tigris |
| Hosting | GitHub Pages + Render |
| OCR | Tesseract |
| PDF Processing | Python PDF tooling |
| Word Processing | `python-docx` |
| API Server | Uvicorn |
| Cloud Storage API | boto3 / S3-compatible API |

---

# Project Status

**Current status: Functional local archive system**

Completed:

- [x] Official paper collection
- [x] Local archive
- [x] Archive inventory
- [x] Metadata verification system
- [x] Verification queue
- [x] Canonical filenames
- [x] Tigris storage