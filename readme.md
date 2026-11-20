# MRSPTU Question Paper Downloader

A web-based tool for downloading previous-year question papers from **Maharaja Ranjit Singh Punjab Technical University (MRSPTU)**.

Enter one or more subject codes, and the downloader searches the available MRSPTU question-paper archives and packages the matching papers into a single ZIP file.

## Features

- 📚 Search question papers by **subject code**
- 🔎 Searches multiple MRSPTU archives automatically
- 📅 Searches in the order:
  - 2024
  - 2023
  - 2022
- 🔤 Supports subject codes with or without spaces/hyphens
  - `BMECS1501`
  - `BMECS 1501`
  - `BMECS1-501`
- 📄 Finds multiple papers for the same subject
- ⚡ Concurrent downloading for faster processing
- 📦 Automatically creates a ZIP containing the downloaded papers
- 📡 Live download status and progress
- 🌐 Gradio-based web interface
- 📱 Designed to be usable from desktop and mobile devices

## How It Works

The application:

1. Accepts subject codes from the user.
2. Normalizes the subject codes.
3. Searches the MRSPTU question-paper archives.
4. Identifies matching question papers.
5. Downloads the available files.
6. Handles different file sources such as direct PDFs and Google-hosted documents.
7. Creates a ZIP file containing the successfully downloaded papers.
8. Provides the ZIP file for download.

## Question Paper Sources

The downloader currently searches:

- [MRSPTU Question Papers 2024](https://library.mrsptu.ac.in/question-paper-2024/)
- [MRSPTU Question Papers 2023](https://library.mrsptu.ac.in/question-paper-2023/)
- [MRSPTU Question Papers 2022](https://library.mrsptu.ac.in/question-papers/)

Search priority:

```text
2024 → 2023 → 2022
```

## Example

Enter subject codes one per line:

```text
BMECS1501
BMAT1101
KMECH503
```

The application searches for all matching papers and produces a ZIP containing the available results.

## Installation

Clone the repository:

```bash
git clone https://github.com/Thorfinn-will-help/MRSPTU-Question-Paper-Downloader.git
```

Enter the project directory:

```bash
cd MRSPTU-Question-Paper-Downloader
```

Install the required packages:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python app.py
```

The Gradio interface will start locally.

## Requirements

- Python 3.9+
- Gradio
- Requests
- BeautifulSoup4

Dependencies are listed in:

```text
requirements.txt
```

## Project Structure

```text
MRSPTU-Question-Paper-Downloader/
│
├── app.py
├── downloader.py
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

### `app.py`

Provides the Gradio web interface and displays the download progress.

### `downloader.py`

Contains the question-paper search, downloading, processing, and ZIP-generation logic.

### `requirements.txt`

Contains the Python dependencies required to run the application.

## Limitations

The downloader depends on the availability and structure of the MRSPTU website and external document-hosting services.

Downloads may fail when:

- A question paper has been removed.
- A document is unavailable.
- A file requires restricted access.
- The MRSPTU website changes its page structure.
- An external document-hosting service changes its download mechanism.

The application reports failed downloads instead of saving invalid HTML pages as question papers.

## Performance

Download time depends on:

- Number of subject codes
- Number of papers found
- MRSPTU server response time
- External file-hosting response time
- Network speed

The downloader uses concurrent downloads to reduce overall processing time.

Typical processing time can vary significantly depending on the number of papers requested.

## Disclaimer

This project is an independent utility for locating and downloading publicly available MRSPTU question papers.

It is **not affiliated with or officially endorsed by Maharaja Ranjit Singh Punjab Technical University (MRSPTU)**.

The availability and legality of individual documents are determined by their respective source websites and copyright holders.

## License

This project is licensed under the **MIT License**.

See the [`LICENSE`](LICENSE) file for details.

## Author

**Thorfinn-will-help**

Built as a student project to make accessing previous-year MRSPTU question papers faster and less painful.