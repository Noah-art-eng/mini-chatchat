const API_BASE = "http://127.0.0.1:8000";

let allDocuments = [];
let openedFile = null;

// =============================
// 1. DOM Elements
// =============================

const questionInput = document.getElementById("question");
const chatHistoryEl = document.getElementById("chat-history");
const documentList = document.getElementById("document-list");
const dropZone = document.getElementById("drop-zone");
const documentSearch = document.getElementById("document-search");
const btnSend = document.getElementById("btn-send");
const btnUpload = document.getElementById("btn-upload");
const btnClear = document.getElementById("btn-clear");
const kbSelector = document.getElementById("kb-selector");
const btnCreateKb = document.getElementById("btn-create-kb");
const btnDeleteKb = document.getElementById("btn-delete-kb");
const chunkSearchInput =
    document.getElementById("chunk-search-input");

const btnSearchChunks =
    document.getElementById("btn-search-chunks");

const chunkSearchResults =
    document.getElementById("chunk-search-results");


// =============================
// 2. Chat Functions
// =============================

async function ask() {
    const question = questionInput.value.trim();
    if (!question) return;

    chatHistoryEl.innerHTML += `
        <div class="message loading">
            <h3 class="assistant-label">Assistant</h3>
            <p>Thinking...</p>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question })
        });

        const data = await response.json();

        const loadingEl = document.querySelector(".loading");
        if (loadingEl) loadingEl.remove();

        const answerText =
            data.answer.includes("insufficient_quota") && data.sources.length > 0
                ? data.sources[0].chunk
                : data.answer;

        const sourcesHTML =
            data.sources.length > 0
                ? data.sources.map(source => `
                    <div class="source-card">
                        <strong
    class="source-link"
    onclick="loadChunkContent(${source.chunk_id})"
>
    ${source.source}
    &middot; chunk ${source.chunk_id}
    &middot; ${source.distance.toFixed(2)}
</strong>
                        <p>${source.chunk}</p>
                    </div>
                  `).join("")
                : "<p>No relevant sources found.</p>";

        chatHistoryEl.innerHTML += `
            <div class="message">
                <h3 class="user-label">User</h3>
                <p>${question}</p>

                <h3 class="assistant-label">Assistant</h3>
                <p>${answerText}</p>

                <h3>Sources</h3>
                <div class="sources">${sourcesHTML}</div>
            </div>
            <hr>
        `;

        saveChatHistory();
        questionInput.value = "";
    } catch (error) {
        console.error(error);
        const loadingEl = document.querySelector(".loading");
        if (loadingEl) loadingEl.remove();
        alert("Server error. Please check backend.");
    }
}


// =============================
// 3. Upload Functions
// =============================

async function uploadFiles(files) {
    if (!files || files.length === 0) {
        alert("Please choose a file first.");
        return;
    }

    try {
        for (const file of files) {
            const formData = new FormData();
            formData.append("file", file);

            await fetch(`${API_BASE}/upload`, {
                method: "POST",
                body: formData
            });
        }

        showToast("Files uploaded successfully", "success");

        loadStats();
        loadDocuments();
    } catch (error) {
        console.error(error);
        showToast("Upload failed. Please check backend.", "error");
    }
}

async function uploadPdf() {
    const files = document.getElementById("pdfFile").files;
    await uploadFiles(files);
}


// =============================
// 4. Knowledge Base Functions
// =============================

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();

        document.getElementById("kb-stats").innerHTML = `
            <p>Files: ${data.file_count} &nbsp;|&nbsp; Chunks: ${data.chunk_count}</p>
            <p>Embedding: ${data.embedding_model}</p>
        `;
    } catch (error) {
        console.error(error);
    }
}

async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE}/documents`);
        const data = await response.json();

        allDocuments = data.files;
        renderDocuments(allDocuments);
    } catch (error) {
        console.error(error);
    }
}

function renderDocuments(files) {
    documentList.innerHTML = files.map(file => `
        <li class="document-item">
            <div class="document-row">
                <strong
                    class="document-name"
                    onclick="toggleFileChunks('${file.filename}')"
                >
                    ${file.filename}
                </strong>

                <span>${file.size} bytes</span>
                <span>${file.time}</span>

                <button onclick="deleteDocument('${file.filename}')">
                    Delete
                </button>
            </div>

            <div
                class="chunk-list"
                id="chunks-${file.filename}"
            ></div>
        </li>
    `).join("");
}

async function toggleFileChunks(filename) {
    const chunkBox = document.getElementById(
        `chunks-${filename}`
    );

    if (openedFile === filename) {
        chunkBox.innerHTML = "";
        openedFile = null;
        return;
    }

    openedFile = filename;

    try {
        const response = await fetch(
            `${API_BASE}/file_docs/${encodeURIComponent(filename)}`
        );

        const data = await response.json();

        chunkBox.innerHTML = data.chunks.length > 0
            ? data.chunks.map(chunk => `
                            <div
                class="chunk-item"
                onclick="loadChunkContent(${chunk.chunk_id})"
            >
                Chunk ${chunk.chunk_id}
            </div>
            `).join("")
            : `<p>No chunks found.</p>`;
    } catch (error) {
        console.error(error);
        showToast(
            "Failed to load chunks.",
            "error"
        );
    }
}

async function loadChunkContent(chunkId) {
    try {
        const response = await fetch(
            `${API_BASE}/chunk/${chunkId}`
        );

        const data = await response.json();

        const chunkViewer =
            document.getElementById("chunk-viewer");

        chunkViewer.innerHTML = `
            <h3>Chunk ${data.chunk_id}</h3>
            <p><strong>Source:</strong> ${data.source}</p>
            <p>${data.text}</p>
        `;
    } catch (error) {
        console.error(error);
        showToast(
            "Failed to load chunk content.",
            "error"
        );
    }
}

async function deleteDocument(filename) {
    const confirmed = confirm(`Delete ${filename}?`);
    if (!confirmed) return;

    try {
        const response = await fetch(
            `${API_BASE}/documents/${encodeURIComponent(filename)}`,
            { method: "DELETE" }
        );

        const data = await response.json();
        alert(data.message);

        loadStats();
        loadDocuments();
    } catch (error) {
        console.error(error);
        alert("Delete failed. Please check backend.");
    }
}

async function createKnowledgeBase() {
    const kbName = prompt("New knowledge base name:");

    if (!kbName) return;

    await fetch(`${API_BASE}/knowledge_bases`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            kb_name: kbName
        })
    });

    await loadKnowledgeBases();

    kbSelector.value = kbName;
    await switchKnowledgeBase();

    showToast("Knowledge base created.", "success");
}

async function deleteKnowledgeBase() {
    const kbName = kbSelector.value;

    if (!kbName) return;

    if (kbName === "default") {
        showToast(
            "Default knowledge base cannot be deleted.",
            "error"
        );
        return;
    }

    const confirmed = confirm(
        `Delete knowledge base "${kbName}"?`
    );

    if (!confirmed) return;

    try {
        const response = await fetch(
            `${API_BASE}/knowledge_bases/${encodeURIComponent(kbName)}`,
            {
                method: "DELETE"
            }
        );

        const data = await response.json();

        if (data.error) {
            showToast(data.error, "error");
            return;
        }

        showToast(data.message, "success");

        await loadKnowledgeBases();

        kbSelector.value = "default";
        await switchKnowledgeBase();

        document.getElementById("chunk-viewer").innerHTML =
            "Select a chunk to preview its content.";

    } catch (error) {
        console.error(error);
        showToast(
            "Failed to delete knowledge base.",
            "error"
        );
    }
}

async function searchChunks() {

    const query =
        chunkSearchInput.value.trim();

    if (!query) return;

    try {

        const response = await fetch(
            `${API_BASE}/search_docs`,
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json"
                },
                body: JSON.stringify({
                    query: query,
                    top_k: 5
                })
            }
        );

        const data = await response.json();

        chunkSearchResults.innerHTML =
            data.results.map(item => `
                <div class="source-card">
                    <strong>
                        ${item.source}
                        · chunk ${item.chunk_id}
                    </strong>

                    <p>
                        Distance:
                        ${item.distance.toFixed(2)}
                    </p>

                    <p>
                        ${item.chunk}
                    </p>
                </div>
            `).join("");

    } catch (error) {

        console.error(error);

        chunkSearchResults.innerHTML =
            "<p>Search failed.</p>";
    }
}


// =============================
// 5. Chat History Functions
// =============================

function saveChatHistory() {
    localStorage.setItem("chatHistory", chatHistoryEl.innerHTML);
}

function restoreChatHistory() {
    const saved = localStorage.getItem("chatHistory");
    if (saved) {
        chatHistoryEl.innerHTML = saved;
    }
}

function clearChatHistory() {
    localStorage.removeItem("chatHistory");
    chatHistoryEl.innerHTML = "";
}

function showToast(message, type = "success") {
    const toastContainer =
        document.getElementById("toast-container");

    const toast = document.createElement("div");

    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    toastContainer.appendChild(toast);

    setTimeout(function () {
        toast.classList.add("hide");

        setTimeout(function () {
            toast.remove();
        }, 300);
    }, 3000);
}

async function loadKnowledgeBases() {
    const response =
        await fetch(`${API_BASE}/knowledge_bases`);

    const data = await response.json();

    kbSelector.innerHTML =
        data.knowledge_bases
            .map(kb => `
                <option value="${kb.kb_name}">
                    ${kb.kb_name}
                </option>
            `)
            .join("");

    if (data.knowledge_bases.length > 0) {
        await switchKnowledgeBase();
    }
}

async function switchKnowledgeBase() {

    const kbName =
        document.getElementById(
            "kb-selector"
        ).value;

    await fetch(
        `${API_BASE}/switch_kb`,
        {
            method: "POST",
            headers: {
                "Content-Type":
                    "application/json"
            },
            body: JSON.stringify({
                kb_name: kbName
            })
        }
    );

    loadStats();
    loadDocuments();
}


// =============================
// 6. Event Listeners
// =============================

btnSend.addEventListener("click", ask);

btnUpload.addEventListener("click", uploadPdf);

btnClear.addEventListener("click", clearChatHistory);

questionInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        ask();
    }
});

dropZone.addEventListener("dragover", function (event) {
    event.preventDefault();
    dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", function () {
    dropZone.classList.remove("drag-over");
});

dropZone.addEventListener("drop", function (event) {
    event.preventDefault();
    dropZone.classList.remove("drag-over");
    uploadFiles(event.dataTransfer.files);
});

documentSearch.addEventListener("input", function () {
    const keyword = documentSearch.value.toLowerCase();
    const filtered = allDocuments.filter(file =>
        file.filename.toLowerCase().includes(keyword)
    );
    renderDocuments(filtered);
});

kbSelector.addEventListener("change", switchKnowledgeBase);

btnCreateKb.addEventListener("click", createKnowledgeBase);

btnDeleteKb.addEventListener("click", deleteKnowledgeBase);

btnSearchChunks.addEventListener("click", searchChunks);

// =============================
// 7. Init
// =============================

restoreChatHistory();
loadKnowledgeBases();
document.getElementById("chunk-viewer").innerHTML =
    "Select a chunk to preview its content.";