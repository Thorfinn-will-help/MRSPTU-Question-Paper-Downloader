import gradio as gr
import threading
import queue
import time

from downloader import download_papers


# ============================================================
# PROCESS REQUEST
# ============================================================

def process_request(subject_text):
    """
    Run the downloader in a background thread and stream
    live status messages to the Gradio interface.
    """

    # --------------------------------------------------------
    # CLEAN INPUT
    # --------------------------------------------------------

    subjects = [
        line.strip()
        for line in subject_text.splitlines()
        if line.strip()
    ]

    # Remove duplicate subject codes
    subjects = list(dict.fromkeys(subjects))

    if not subjects:
        raise gr.Error(
            "Please enter at least one subject code."
        )

    # --------------------------------------------------------
    # MESSAGE QUEUE
    # --------------------------------------------------------

    messages = queue.Queue()

    result = {
        "zip_path": None,
        "error": None,
        "finished": False,
    }

    # --------------------------------------------------------
    # CALLBACK
    # --------------------------------------------------------

    def status_callback(message):
        """
        Called by downloader.py whenever something important
        happens.
        """

        messages.put(message)

    # --------------------------------------------------------
    # DOWNLOADER THREAD
    # --------------------------------------------------------

    def run_downloader():

        try:

            zip_path = download_papers(
                subjects,
                status_callback=status_callback,
            )

            result["zip_path"] = zip_path

        except Exception as error:

            result["error"] = str(error)

        finally:

            result["finished"] = True

            # Wake up the generator
            messages.put(None)

    # Start downloader in background
    thread = threading.Thread(
        target=run_downloader,
        daemon=True,
    )

    thread.start()

    # --------------------------------------------------------
    # LIVE STATUS
    # --------------------------------------------------------

    status_lines = []

    while True:

        try:

            message = messages.get(
                timeout=0.25
            )

            # None means downloader finished
            if message is None:
                break

            status_lines.append(message)

            # Keep the log from becoming ridiculously huge
            if len(status_lines) > 100:
                status_lines = status_lines[-100:]

            formatted_status = "\n".join(
                f"• {line}"
                for line in status_lines
            )

            yield (
                formatted_status,
                None,
            )

        except queue.Empty:

            # Downloader is still working
            if not result["finished"]:
                continue

            break

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    if result["error"]:

        raise gr.Error(
            result["error"]
        )

    final_status = "\n".join(
        f"• {line}"
        for line in status_lines
    )

    yield (
        final_status,
        result["zip_path"],
    )


# ============================================================
# USER INTERFACE
# ============================================================

with gr.Blocks(
    title="MRSPTU Question Paper Downloader"
) as app:

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    gr.Markdown(
        """
# 📚 MRSPTU Question Paper Downloader

Download previous-year MRSPTU question papers by entering
their **subject codes**.

The system searches:

**2024 → 2023 → 2022**
"""
    )

    # --------------------------------------------------------
    # TIME INFORMATION
    # --------------------------------------------------------

    gr.Markdown(
        """
### ⏱️ Approximate processing time

The more papers requested, the longer the download will take.

| Request | Example | Approx. time |
|---|---:|---:|
| Small | 1 subject / ~7 papers | ~30 sec |
| Medium | 3–5 subjects | ~1–2 min |
| Large | 9 subjects / ~53 papers | ~3.5 min |

Times are approximate and depend on the MRSPTU server,
network speed, and the number of papers found.
"""
    )

    # --------------------------------------------------------
    # INPUT
    # --------------------------------------------------------

    subject_input = gr.Textbox(
        label="Subject Codes",
        placeholder=(
            "Enter one subject code per line\n\n"
            "Example:\n"
            "BMECS1501\n"
            "BMAT1101\n"
            "KMECH503"
        ),
        lines=10,
    )

    # --------------------------------------------------------
    # BUTTONS
    # --------------------------------------------------------

    with gr.Row():

        download_button = gr.Button(
            "⬇️ Download Question Papers",
            variant="primary",
        )

        clear_button = gr.ClearButton(
            components=[
                subject_input,
            ],
            value="Clear",
        )

    # --------------------------------------------------------
    # STATUS PANEL
    # --------------------------------------------------------

    gr.Markdown(
        "### 📡 Download Status"
    )

    status_box = gr.Markdown(
        value=(
            "Waiting for download..."
        )
    )

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    gr.Markdown(
        "### 📦 Result"
    )

    output_file = gr.File(
        label="Your Question Papers"
    )

    # --------------------------------------------------------
    # DOWNLOAD ACTION
    # --------------------------------------------------------

    download_button.click(
        fn=process_request,
        inputs=subject_input,
        outputs=[
            status_box,
            output_file,
        ],
    )


# ============================================================
# LAUNCH
# ============================================================

if __name__ == "__main__":
    app.launch()