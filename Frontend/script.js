const API_URL = "http://127.0.0.1:8000";


const downloadBtn =
    document.getElementById("downloadBtn");

const themeBtn =
    document.getElementById("themeBtn");

const subjectsInput =
    document.getElementById("subjects");

const terminal =
    document.getElementById("terminal");

const logs =
    document.getElementById("logs");

const percentage =
    document.getElementById("percentage");

const progressFill =
    document.getElementById("progressFill");

const eta =
    document.getElementById("eta");

const elapsed =
    document.getElementById("elapsed");

const terminalStatus =
    document.getElementById("terminalStatus");

const status =
    document.getElementById("status");


// ============================================================
// DARK / LIGHT MODE
// ============================================================

themeBtn.onclick = () => {

    document.body.classList.toggle("dark");

    const dark =
        document.body.classList.contains("dark");

    themeBtn.textContent =
        dark ? "🌙" : "☀️";

    localStorage.setItem(
        "mrsptu-theme",
        dark ? "dark" : "light"
    );
};


// Restore theme

if (
    localStorage.getItem("mrsptu-theme")
    === "dark"
) {

    document.body.classList.add("dark");

    themeBtn.textContent = "🌙";

}


// ============================================================
// ADD TERMINAL LOG
// ============================================================

function addLog(message) {

    const line =
        document.createElement("div");

    line.className = "log-line";

    line.textContent =
        "> " + message;

    logs.appendChild(line);

    logs.scrollTop =
        logs.scrollHeight;
}


// ============================================================
// FORMAT ELAPSED TIME
// ============================================================

function formatElapsed(seconds) {

    seconds =
        Math.floor(seconds);

    const minutes =
        Math.floor(seconds / 60);

    const secs =
        seconds % 60;

    return (
        String(minutes).padStart(2, "0")
        + ":"
        + String(secs).padStart(2, "0")
    );
}


// ============================================================
// DOWNLOAD
// ============================================================

downloadBtn.onclick = async () => {

    const text =
        subjectsInput.value;

    const subjects =
        text
            .split("\n")
            .map(x => x.trim().toUpperCase())
            .filter(x => x);


    if (subjects.length === 0) {

        status.textContent =
            "Enter at least one subject code.";

        return;
    }


    // Reset UI

    terminal.classList.remove("hidden");

    logs.innerHTML = "";

    percentage.textContent = "0%";

    progressFill.style.width = "0%";

    eta.textContent = "ETA: --:--";

    elapsed.textContent =
        "Elapsed: 00:00";

    terminalStatus.textContent =
        "Starting...";

    status.textContent = "";

    downloadBtn.disabled = true;


    const startTime =
        Date.now();


    try {

        // ====================================================
        // START JOB
        // ====================================================

        addLog(
            `Starting download for ${subjects.length} subject(s)...`
        );


        const response =
            await fetch(
                `${API_URL}/download`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        subjects: subjects
                    })
                }
            );


        if (!response.ok) {

            const error =
                await response.json();

            throw new Error(
                error.detail ||
                "Could not start download."
            );
        }


        const data =
            await response.json();

        const jobId =
            data.job_id;


        addLog(
            `Job started: ${jobId.substring(0, 8)}`
        );


        // ====================================================
        // CHECK STATUS
        // ====================================================

        while (true) {

            await new Promise(
                resolve =>
                    setTimeout(resolve, 1000)
            );


            const statusResponse =
                await fetch(
                    `${API_URL}/status/${jobId}`
                );


            if (!statusResponse.ok) {

                throw new Error(
                    "Could not read download status."
                );
            }


            const job =
                await statusResponse.json();


            // Progress

            const progress =
                job.progress || 0;

            percentage.textContent =
                `${progress}%`;

            progressFill.style.width =
                `${progress}%`;


            // ETA

            eta.textContent =
                `ETA: ${job.eta || "--:--"}`;


            // Elapsed

            const seconds =
                (Date.now() - startTime)
                / 1000;

            elapsed.textContent =
                `Elapsed: ${formatElapsed(seconds)}`;


            // Terminal status

            terminalStatus.textContent =
                job.status;


            // Add meaningful new log

            if (
                job.message &&
                job.message !==
                window.lastDownloaderMessage
            ) {

                addLog(job.message);

                window.lastDownloaderMessage =
                    job.message;
            }


            // =================================================
            // COMPLETE
            // =================================================

            if (
                job.status ===
                "completed"
            ) {

                percentage.textContent =
                    "100%";

                progressFill.style.width =
                    "100%";

                eta.textContent =
                    "ETA: 00:00";

                terminalStatus.textContent =
                    "Completed";


                addLog(
                    "ZIP is ready. Starting download..."
                );


                const zipResponse =
                    await fetch(
                        `${API_URL}/download/${jobId}`
                    );


                if (!zipResponse.ok) {

                    throw new Error(
                        "ZIP download failed."
                    );
                }


                const blob =
                    await zipResponse.blob();


                const url =
                    window.URL.createObjectURL(
                        blob
                    );


                const a =
                    document.createElement("a");

                a.href = url;

                a.download =
                    "MRSPTU_Question_Papers.zip";

                document.body.appendChild(a);

                a.click();

                a.remove();

                window.URL.revokeObjectURL(url);


                status.textContent =
                    "Download complete.";

                break;
            }


            // =================================================
            // ERROR
            // =================================================

            if (
                job.status ===
                "error"
            ) {

                throw new Error(
                    job.error ||
                    "Downloader failed."
                );
            }

        }

    } catch (error) {

        addLog(
            `ERROR: ${error.message}`
        );

        terminalStatus.textContent =
            "Error";

        status.textContent =
            error.message;

    } finally {

        downloadBtn.disabled =
            false;

    }

};