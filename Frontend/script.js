const API_URL = "https://mrsptu-question-paper-downloader-1.onrender.com";

let searchMode = "subject_code";
let lastResults = [];
let searchStartTime = null;
let timerInterval = null;


// ============================================================
// DOM ELEMENTS
// ============================================================

const searchInput = document.getElementById("subjects");
const searchButton = document.getElementById("downloadBtn");

const themeBtn = document.getElementById("themeBtn");

const subjectModeBtn =
    document.getElementById("subjectModeBtn");

const paperIdModeBtn =
    document.getElementById("paperIdModeBtn");

const inputHint =
    document.getElementById("inputHint");

const resultsSection =
    document.getElementById("resultsSection");

const progressFill =
    document.getElementById("progressFill");

const progressPercent =
    document.getElementById("progressPercent");

const elapsed =
    document.getElementById("elapsed");

const eta =
    document.getElementById("eta");

const statusText =
    document.getElementById("statusText");

const status =
    document.getElementById("status");


// ============================================================
// SEARCH MODE
// ============================================================

subjectModeBtn.addEventListener("click", () => {

    searchMode = "subject_code";

    subjectModeBtn.classList.add("active");
    paperIdModeBtn.classList.remove("active");

    searchInput.placeholder =
        "BMECS1501\nBMECS1502\nBMECS1503";

    inputHint.textContent =
        "Enter one subject code per line. Spaces and hyphens are automatically ignored.";
});


paperIdModeBtn.addEventListener("click", () => {

    searchMode = "paper_id";

    paperIdModeBtn.classList.add("active");
    subjectModeBtn.classList.remove("active");

    searchInput.placeholder =
        "23440104\n23440105\n23440106";

    inputHint.textContent =
        "Enter one Paper ID per line.";
});


// ============================================================
// SEARCH BUTTON
// ============================================================

searchButton.addEventListener(
    "click",
    searchPapers
);


// ============================================================
// SEARCH PAPERS
// ============================================================

async function searchPapers() {

    const rawInput =
        searchInput.value.trim();


    if (!rawInput) {

        showStatus(
            "Please enter a Subject Code or Paper ID."
        );

        return;
    }


    /*
     * Split input by lines.
     */

    const values =
        rawInput
            .split(/\r?\n/)
            .map(value => value.trim())
            .filter(Boolean);


    if (values.length === 0) {

        showStatus(
            "Please enter a valid search value."
        );

        return;
    }


    /*
     * Reset previous search.
     */

    lastResults = [];

    searchButton.disabled = true;

    setProgress(5);

    searchStartTime = Date.now();

    clearInterval(timerInterval);

    timerInterval =
        setInterval(
            updateElapsedTime,
            100
        );


    showStatus(
        `Searching ${values.length} ${
            values.length === 1
                ? "query"
                : "queries"
        }...`
    );


    /*
     * Remove old results.
     */

    const oldDownloadAll =
        document.getElementById(
            "downloadAllBtn"
        );

    if (oldDownloadAll) {
        oldDownloadAll.remove();
    }


    /*
     * IMPORTANT:
     *
     * Run all searches simultaneously.
     *
     * Previously the code waited for:
     *
     * query 1 → query 2 → query 3
     *
     * Now:
     *
     * query 1 ─┐
     * query 2 ─┼→ simultaneously
     * query 3 ─┘
     */

    try {

        const requests =
            values.map(
                value => searchSingleValue(value)
            );


        const results =
            await Promise.all(requests);


        /*
         * Combine all returned arrays.
         */

        const allResults =
            results.flat();


        /*
         * Remove duplicate database records.
         */

        const uniqueResults = [];

        const seen =
            new Set();


        for (const paper of allResults) {

            if (!seen.has(paper.id)) {

                seen.add(paper.id);

                uniqueResults.push(paper);
            }
        }


        lastResults =
            uniqueResults;


        setProgress(100);


        if (lastResults.length === 0) {

            showStatus(
                "Search complete. No papers found."
            );


            renderEmptyResults();

            return;
        }


        /*
         * Sort:
         *
         * Year: newest first
         * Subject: alphabetical
         * Sequence: ascending
         */

        lastResults.sort(
            (a, b) => {

                if (
                    Number(a.year) !==
                    Number(b.year)
                ) {

                    return (
                        Number(b.year) -
                        Number(a.year)
                    );
                }


                if (
                    String(a.subject_code || "") !==
                    String(b.subject_code || "")
                ) {

                    return String(
                        a.subject_code || ""
                    ).localeCompare(
                        String(
                            b.subject_code || ""
                        )
                    );
                }


                return (
                    Number(
                        a.sequence_number || 0
                    ) -
                    Number(
                        b.sequence_number || 0
                    )
                );
            }
        );


        showStatus(
            `Found ${lastResults.length} paper${
                lastResults.length === 1
                    ? ""
                    : "s"
            }.`
        );


        renderResults(
            lastResults
        );


        createDownloadAllButton();


    } catch (error) {

        console.error(
            "SEARCH ERROR:",
            error
        );


        setProgress(100);


        if (
            error.name ===
            "AbortError"
        ) {

            showStatus(
                "Search timed out after 15 seconds."
            );


            renderError(
                "Search timed out",
                "The archive server did not respond within 15 seconds."
            );

        } else {

            showStatus(
                "Search failed."
            );


            renderError(
                "Unable to search archive",
                error.message
            );
        }

    } finally {

        searchButton.disabled = false;

        clearInterval(
            timerInterval
        );
    }
}


// ============================================================
// SINGLE SEARCH REQUEST
// ============================================================

async function searchSingleValue(
    value
) {

    const params =
        new URLSearchParams();


    /*
     * Subject Code search
     */

    if (
        searchMode ===
        "subject_code"
    ) {

        /*
         * Remove spaces and hyphens.
         *
         * Example:
         *
         * ME-CS-501
         * ME CS 501
         *
         * becomes:
         *
         * MECS501
         */

        const normalized =
            value
                .replace(
                    /[\s-]/g,
                    ""
                )
                .toUpperCase();


        params.append(
            "subject_code",
            normalized
        );


    /*
     * Paper ID search
     */

    } else {

        params.append(
            "paper_id",
            value.trim()
        );
    }


    params.append(
        "limit",
        "100"
    );


    /*
     * Abort request after 15 seconds.
     */

    const controller =
        new AbortController();


    const timeout =
        setTimeout(
            () => {
                controller.abort();
            },
            15000
        );


    try {

        const response =
            await fetch(
                `${API_URL}/papers?${params.toString()}`,
                {
                    method: "GET",
                    signal: controller.signal,
                    cache: "no-store"
                }
            );


        if (!response.ok) {

            let message =
                `HTTP ${response.status}`;


            try {

                const errorData =
                    await response.json();


                if (
                    errorData.detail
                ) {

                    message =
                        errorData.detail;
                }

            } catch (_) {
                // Ignore JSON parsing failure.
            }


            throw new Error(
                message
            );
        }


        const data =
            await response.json();


        return data.papers || [];


    } finally {

        clearTimeout(
            timeout
        );
    }
}


// ============================================================
// RENDER RESULTS
// ============================================================

function renderResults(
    papers
) {

    /*
     * IMPORTANT:
     *
     * The HTML contains #resultsSection.
     *
     * We create the result content directly inside it.
     */

    resultsSection.innerHTML = "";


    /*
     * Group by Subject Code.
     */

    const grouped = {};


    papers.forEach(
        paper => {

            const subject =
                paper.subject_code ||
                "Unknown Subject";


            if (!grouped[subject]) {

                grouped[subject] = [];
            }


            grouped[subject].push(
                paper
            );
        }
    );


    /*
     * Create groups.
     */

    Object.keys(grouped)
        .sort()
        .forEach(
            subjectCode => {

                const subjectGroup =
                    document.createElement(
                        "div"
                    );


                subjectGroup.className =
                    "subject-group";


                const subjectPapers =
                    grouped[
                        subjectCode
                    ];


                /*
                 * Subject heading
                 */

                const heading =
                    document.createElement(
                        "div"
                    );


                heading.className =
                    "subject-heading";


                heading.innerHTML = `
                    <div>
                        <span class="subject-label">
                            SUBJECT CODE
                        </span>

                        <h3>
                            ${escapeHTML(
                                subjectCode
                            )}
                        </h3>
                    </div>

                    <span class="subject-count">
                        ${
                            subjectPapers.length
                        }
                        ${
                            subjectPapers.length === 1
                                ? "paper"
                                : "papers"
                        }
                    </span>
                `;


                subjectGroup.appendChild(
                    heading
                );


                /*
                 * Group by year.
                 */

                const years = {};


                subjectPapers.forEach(
                    paper => {

                        const year =
                            paper.year ||
                            "Unknown";


                        if (!years[year]) {

                            years[year] = [];
                        }


                        years[year].push(
                            paper
                        );
                    }
                );


                /*
                 * Newest year first.
                 */

                Object.keys(years)
                    .sort(
                        (a, b) =>
                            Number(b) -
                            Number(a)
                    )
                    .forEach(
                        year => {

                            const yearGroup =
                                document.createElement(
                                    "div"
                                );


                            yearGroup.className =
                                "year-group";


                            yearGroup.innerHTML = `
                                <div class="year-heading">

                                    <span>
                                        ${escapeHTML(
                                            String(year)
                                        )}
                                    </span>

                                    <div class="year-line"></div>

                                </div>

                                <div class="paper-list"></div>
                            `;


                            const paperList =
                                yearGroup.querySelector(
                                    ".paper-list"
                                );


                            years[year]
                                .sort(
                                    (
                                        a,
                                        b
                                    ) =>
                                        Number(
                                            a.sequence_number ||
                                            0
                                        ) -
                                        Number(
                                            b.sequence_number ||
                                            0
                                        )
                                )
                                .forEach(
                                    paper => {

                                        paperList.appendChild(
                                            createPaperCard(
                                                paper
                                            )
                                        );
                                    }
                                );


                            subjectGroup.appendChild(
                                yearGroup
                            );
                        }
                    );


                resultsSection.appendChild(
                    subjectGroup
                );
            }
        );
}


// ============================================================
// PAPER CARD
// ============================================================

function createPaperCard(
    paper
) {

    const card =
        document.createElement(
            "div"
        );


    card.className =
        "paper-card";


    const fileType =
        String(
            paper.file_type || ""
        ).toUpperCase();


    const paperId =
        paper.paper_id ||
        "Unavailable";


    const sequence =
        paper.sequence_number
            ? `Paper ${paper.sequence_number}`
            : "Paper";


    card.innerHTML = `

        <div class="file-icon">
            ${escapeHTML(
                fileType
            )}
        </div>

        <div class="paper-info">

            <div class="paper-title">
                ${escapeHTML(
                    sequence
                )}
            </div>

            <div class="paper-meta">

                <span>
                    ${escapeHTML(
                        String(
                            paper.year ||
                            ""
                        )
                    )}
                </span>

                <span class="meta-separator">
                    •
                </span>

                <span>
                    ID:
                    ${escapeHTML(
                        String(
                            paperId
                        )
                    )}
                </span>

                <span class="meta-separator">
                    •
                </span>

                <span>
                    ${escapeHTML(
                        fileType
                    )}
                </span>

            </div>

            <div class="paper-meta">
                ${escapeHTML(
                    paper.file_name ||
                    ""
                )}
            </div>

        </div>

        <button
            class="individual-download"
            type="button"
        >
            Download
        </button>
    `;


    const downloadButton =
        card.querySelector(
            ".individual-download"
        );


    downloadButton.addEventListener(
        "click",
        () => {

            downloadIndividualPaper(
                paper.id
            );
        }
    );


    return card;
}


// ============================================================
// INDIVIDUAL DOWNLOAD
// ============================================================

function downloadIndividualPaper(
    databaseId
) {

    if (!databaseId) {

        showStatus(
            "Invalid paper record."
        );

        return;
    }


    const url =
        `${API_URL}/papers/` +
        `${encodeURIComponent(
            databaseId
        )}/download`;


    /*
     * Let the browser handle the file download.
     */

    window.location.href =
        url;
}


// ============================================================
// DOWNLOAD ALL BUTTON
// ============================================================

function createDownloadAllButton() {

    /*
     * Remove old button.
     */

    const existing =
        document.getElementById(
            "downloadAllBtn"
        );


    if (existing) {

        existing.remove();
    }


    if (
        !lastResults.length
    ) {

        return;
    }


    /*
     * Button sits outside individual
     * paper cards.
     */

    const button =
        document.createElement(
            "button"
        );


    button.id =
        "downloadAllBtn";


    button.className =
        "download-all-btn";


    button.type =
        "button";


    button.textContent =
        `Download All (${lastResults.length})`;


    button.addEventListener(
        "click",
        downloadAllPapers
    );


    /*
     * Put button at the top of results.
     */

    resultsSection.prepend(
        button
    );
}


// ============================================================
// DOWNLOAD ALL
// ============================================================

async function downloadAllPapers() {

    if (
        !lastResults.length
    ) {

        showStatus(
            "There are no papers to download."
        );

        return;
    }


    const ids =
        lastResults
            .map(
                paper => paper.id
            )
            .filter(
                Boolean
            );


    if (!ids.length) {

        showStatus(
            "No downloadable papers found."
        );

        return;
    }


    const button =
        document.getElementById(
            "downloadAllBtn"
        );


    if (button) {

        button.disabled = true;

        button.textContent =
            "Preparing ZIP...";
    }


    showStatus(
        `Preparing ${ids.length} papers...`
    );


    setProgress(10);


    try {

        const response =
            await fetch(
                `${API_URL}/papers/download-zip`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        paper_ids: ids
                    })
                }
            );


        if (!response.ok) {

            let message =
                `HTTP ${response.status}`;


            try {

                const errorData =
                    await response.json();


                if (
                    errorData.detail
                ) {

                    message =
                        errorData.detail;
                }

            } catch (_) {}


            throw new Error(
                message
            );
        }


        setProgress(70);


        const blob =
            await response.blob();


        setProgress(100);


        const url =
            window.URL.createObjectURL(
                blob
            );


        const link =
            document.createElement(
                "a"
            );


        link.href =
            url;


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


        showStatus(
            `Downloaded ${ids.length} papers.`
        );


    } catch (error) {

        console.error(
            "ZIP ERROR:",
            error
        );


        showStatus(
            "Unable to create ZIP file."
        );


        renderError(
            "Download All failed",
            error.message
        );


    } finally {

        if (button) {

            button.disabled = false;

            button.textContent =
                `Download All (${lastResults.length})`;
        }
    }
}


// ============================================================
// EMPTY RESULTS
// ============================================================

function renderEmptyResults() {

    resultsSection.innerHTML = `

        <div class="results-placeholder">

            <div class="placeholder-icon">
                ⌕
            </div>

            <h2>
                No papers found
            </h2>

            <p>
                Nothing in the archive matched your search.
            </p>

        </div>
    `;
}


// ============================================================
// ERROR RESULTS
// ============================================================

function renderError(
    title,
    message
) {

    resultsSection.innerHTML = `

        <div class="results-card error-card">

            <div class="result-message-icon">
                !
            </div>

            <h2>
                ${escapeHTML(title)}
            </h2>

            <p>
                ${escapeHTML(message)}
            </p>

        </div>
    `;
}


// ============================================================
// STATUS
// ============================================================

function showStatus(
    message
) {

    if (statusText) {

        /*
         * First line
         */

        statusText.textContent =
            message;
    }


    if (status) {

        status.textContent =
            message;
    }
}


// ============================================================
// PROGRESS
// ============================================================

function setProgress(
    value
) {

    const percentage =
        Math.max(
            0,
            Math.min(
                100,
                value
            )
        );


    if (progressFill) {

        progressFill.style.width =
            `${percentage}%`;
    }


    if (progressPercent) {

        progressPercent.textContent =
            `${Math.round(
                percentage
            )}%`;
    }
}


// ============================================================
// ELAPSED TIME
// ============================================================

function updateElapsedTime() {

    if (
        !searchStartTime
    ) {

        return;
    }


    const seconds =
        (
            Date.now() -
            searchStartTime
        ) / 1000;


    if (elapsed) {

        if (seconds < 60) {

            elapsed.textContent =
                `${seconds.toFixed(1)}s`;

        } else {

            const minutes =
                Math.floor(
                    seconds / 60
                );

            const remaining =
                Math.floor(
                    seconds % 60
                );

            elapsed.textContent =
                `${String(minutes).padStart(2, "0")}:` +
                `${String(remaining).padStart(2, "0")}`;
        }
    }
}


// ============================================================
// DARK MODE
// ============================================================

themeBtn.addEventListener(
    "click",
    () => {

        document.body.classList.toggle(
            "dark"
        );


        const isDark =
            document.body.classList.contains(
                "dark"
            );


        localStorage.setItem(
            "mrsptu-dark-mode",
            isDark
                ? "true"
                : "false"
        );


        themeBtn.textContent =
            isDark
                ? "☀"
                : "☾";
    }
);


// ============================================================
// LOAD SAVED DARK MODE
// ============================================================

(function loadTheme() {

    const saved =
        localStorage.getItem(
            "mrsptu-dark-mode"
        );


    if (
        saved === "true"
    ) {

        document.body.classList.add(
            "dark"
        );


        themeBtn.textContent =
            "☀";
    }

})();


// ============================================================
// HTML ESCAPE
// ============================================================

function escapeHTML(
    value
) {

    return String(
        value
    )
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            '"',
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );
}
