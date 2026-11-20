// =========================================================
// CONFIGURATION
// =========================================================

// Replace this with your Render FastAPI URL.
//
// Example:
// const API_URL = "https://mrsptu-downloader-api.onrender.com";

const API_URL = "https://YOUR-RENDER-BACKEND.onrender.com";


// =========================================================
// ELEMENTS
// =========================================================

const subjectsInput =
    document.getElementById("subjects");

const downloadBtn =
    document.getElementById("downloadBtn");

const themeBtn =
    document.getElementById("themeBtn");

const terminal =
    document.getElementById("terminal");

const progressFill =
    document.getElementById("progressFill");

const progressPercent =
    document.getElementById("progressPercent");

const etaElement =
    document.getElementById("eta");

const elapsedElement =
    document.getElementById("elapsed");

const statusElement =
    document.getElementById("status");

const statusText =
    document.getElementById("statusText");


// =========================================================
// THEME
// =========================================================

function applyTheme(theme) {

    if (theme === "dark") {

        document.body.classList.add("dark");

        themeBtn.textContent = "☀️";

    } else {

        document.body.classList.remove("dark");

        themeBtn.textContent = "🌙";
    }
}


const savedTheme =
    localStorage.getItem("mrsptu-theme") || "light";

applyTheme(savedTheme);


themeBtn.onclick = () => {

    const dark =
        document.body.classList.contains("dark");

    const newTheme =
        dark ? "light" : "dark";

    applyTheme(newTheme);

    localStorage.setItem(
        "mrsptu-theme",
        newTheme
    );
};


// =========================================================
// TERMINAL
// =========================================================

function addTerminalLine(message) {

    const line =
        document.createElement("div");

    line.className =
        "terminal-line";

    line.innerHTML = `
        <span class="terminal-prompt">&gt;</span>
        <span>${escapeHtml(message)}</span>
    `;

    terminal.appendChild(line);

    terminal.scrollTop =
        terminal.scrollHeight;
}


function clearTerminal() {

    terminal.innerHTML = "";
}


function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}


// =========================================================
// TIME FORMAT
// =========================================================

function formatSeconds(seconds) {

    if (
        seconds === null ||
        seconds === undefined ||
        isNaN(seconds)
    ) {
        return "--:--";
    }

    seconds =
        Math.max(0, Math.floor(seconds));

    const minutes =
        Math.floor(seconds / 60);

    const remaining =
        seconds % 60;

    return (
        String(minutes).padStart(2, "0") +
        ":" +
        String(remaining).padStart(2, "0")
    );
}


// =========================================================
// DOWNLOAD
// =========================================================

downloadBtn.onclick = async () => {

    const text =
        subjectsInput.value.trim();


    const subjects =
        text
            .split(/\r?\n/)
            .map(x => x.trim())
            .filter(x => x);


    // -----------------------------------------------------
    // VALIDATION
    // -----------------------------------------------------

    if (subjects.length === 0) {

        statusElement.textContent =
            "Enter at least one subject code.";

        statusText.textContent =
            "Error";

        return;
    }


    // -----------------------------------------------------
    // RESET UI
    // -----------------------------------------------------

    clearTerminal();

    progressFill.style.width = "0%";

    progressPercent.textContent =
        "0%";

    etaElement.textContent =
        "ETA: --:--";

    elapsedElement.textContent =
        "00:00";

    statusElement.textContent =
        "Starting";

    statusText.textContent =
        "Starting";

    downloadBtn.disabled = true;


    addTerminalLine(
        `Starting download for ${subjects.length} subject(s)...`
    );


    let jobId = null;

    let pollInterval = null;


    try {

        // =================================================
        // START JOB
        // =================================================

        const response =
            await fetch(`${API_URL}/download`, {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    subjects: subjects
                })
            });


        if (!response.ok) {

            const errorText =
                await response.text();

            throw new Error(
                errorText ||
                `Server returned ${response.status}`
            );
        }


        const data =
            await response.json();


        jobId =
            data.job_id;


        if (!jobId) {

            throw new Error(
                "Server did not return a job ID."
            );
        }


        addTerminalLine(
            `Job started: ${jobId}`
        );


        statusElement.textContent =
            "Downloading";

        statusText.textContent =
            "Running";


        // =================================================
        // POLL STATUS
        // =================================================

        pollInterval =
            setInterval(
                () => checkStatus(jobId),
                1000
            );


        // Immediately check once
        await checkStatus(jobId);


    } catch (error) {

        console.error(error);

        addTerminalLine(
            `ERROR: ${error.message}`
        );

        statusElement.textContent =
            "Error";

        statusText.textContent =
            "Error";

        downloadBtn.disabled = false;


        if (pollInterval) {

            clearInterval(
                pollInterval
            );
        }
    }


    // =====================================================
    // STATUS CHECK
    // =====================================================

    async function checkStatus(id) {

        try {

            const response =
                await fetch(
                    `${API_URL}/status/${id}`
                );


            if (!response.ok) {

                throw new Error(
                    `Status request failed: ${response.status}`
                );
            }


            const data =
                await response.json();


            // ------------------------------------------------
            // PROGRESS
            // ------------------------------------------------

            const progress =
                Number(data.progress || 0);


            progressFill.style.width =
                `${progress}%`;


            progressPercent.textContent =
                `${Math.round(progress)}%`;


            // ------------------------------------------------
            // ETA
            // ------------------------------------------------

            if (
                data.eta !== null &&
                data.eta !== undefined
            ) {

                etaElement.textContent =
                    `ETA: ${formatSeconds(data.eta)}`;

            } else {

                etaElement.textContent =
                    "ETA: calculating...";
            }


            // ------------------------------------------------
            // ELAPSED
            // ------------------------------------------------

            if (
                data.elapsed !== null &&
                data.elapsed !== undefined
            ) {

                elapsedElement.textContent =
                    formatSeconds(data.elapsed);
            }


            // ------------------------------------------------
            // STATUS
            // ------------------------------------------------

            if (data.message) {

                addTerminalLine(
                    data.message
                );
            }


            // ------------------------------------------------
            // COMPLETED
            // ------------------------------------------------

            if (
                data.status === "completed"
            ) {

                clearInterval(
                    pollInterval
                );


                progressFill.style.width =
                    "100%";

                progressPercent.textContent =
                    "100%";

                etaElement.textContent =
                    "ETA: 00:00";


                statusElement.textContent =
                    "Complete";

                statusText.textContent =
                    "Complete";


                addTerminalLine(
                    "Download completed."
                );


                // ---------------------------------------------
                // DOWNLOAD ZIP
                // ---------------------------------------------

                const fileResponse =
                    await fetch(
                        `${API_URL}/download/${id}`
                    );


                if (!fileResponse.ok) {

                    throw new Error(
                        "Could not retrieve ZIP file."
                    );
                }


                const blob =
                    await fileResponse.blob();


                const url =
                    window.URL.createObjectURL(
                        blob
                    );


                const link =
                    document.createElement("a");


                link.href = url;

                link.download =
                    "MRSPTU_Question_Papers.zip";


                document.body.appendChild(
                    link
                );


                link.click();


                link.remove();


                window.URL.revokeObjectURL(
                    url
                );


                addTerminalLine(
                    "ZIP file downloaded."
                );


                downloadBtn.disabled =
                    false;
            }


            // ------------------------------------------------
            // FAILED
            // ------------------------------------------------

            if (
                data.status === "failed"
            ) {

                clearInterval(
                    pollInterval
                );


                statusElement.textContent =
                    "Failed";

                statusText.textContent =
                    "Failed";


                addTerminalLine(
                    data.error ||
                    "Download failed."
                );


                downloadBtn.disabled =
                    false;
            }

        } catch (error) {

            console.error(
                "Status error:",
                error
            );

            clearInterval(
                pollInterval
            );


            statusElement.textContent =
                "Error";

            statusText.textContent =
                "Error";


            addTerminalLine(
                `ERROR: ${error.message}`
            );


            downloadBtn.disabled =
                false;
        }
    }
};