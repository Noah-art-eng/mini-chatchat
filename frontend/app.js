const API_BASE = "http://127.0.0.1:8000";

let allDocuments = [];
let openedFile = null;
let currentTempKbId = null;
let currentConversationId = null;

// =============================
// 1. DOM Elements
// =============================

const questionInput = document.getElementById("question");
const chatModeSelect = document.getElementById("chat-mode");
const btnNewConversation =
    document.getElementById("btn-new-conversation");
const currentConversationLabel =
    document.getElementById("current-conversation-label");
const conversationList =
    document.getElementById("conversation-list");
const debugTopKInput = document.getElementById("debug-top-k");
const debugScoreThresholdInput =
    document.getElementById("debug-score-threshold");
const debugPromptNameSelect =
    document.getElementById("debug-prompt-name");
const debugRerankInput =
    document.getElementById("debug-rerank");
const debugRerankTopNInput =
    document.getElementById("debug-rerank-top-n");
const debugReturnDirectInput =
    document.getElementById("debug-return-direct");
const btnDebugSearch =
    document.getElementById("btn-debug-search");
const debugResults =
    document.getElementById("debug-results");
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
const btnExportKb = document.getElementById("btn-export-kb");
const kbImportFileInput = document.getElementById("kb-import-file");
const btnImportKb = document.getElementById("btn-import-kb");
const chunkSearchInput =
    document.getElementById("chunk-search-input");

const btnSearchChunks =
    document.getElementById("btn-search-chunks");

const chunkSearchResults =
    document.getElementById("chunk-search-results");

const tempFileInput = document.getElementById("temp-file");
const btnTempUpload = document.getElementById("btn-temp-upload");
const tempKbIdEl = document.getElementById("temp-kb-id");
const tempQuestionInput = document.getElementById("temp-question");
const btnTempAsk = document.getElementById("btn-temp-ask");
const tempAnswerText = document.getElementById("temp-answer-text");
const tempSources = document.getElementById("temp-sources");


// =============================
// 2. Chat Functions
// =============================

function normalizeSources(sources) {
    if (!Array.isArray(sources)) return [];

    return sources.map((source, index) => {
        if (typeof source === "string") {
            return {
                source: `Source ${index + 1}`,
                title: `Source ${index + 1}`,
                chunk: source,
                chunk_id: index + 1,
                distance: 0
            };
        }

        const distance = Number(source.distance ?? 0);
        const rerankScore =
            source.rerank_score === undefined
                ? null
                : Number(source.rerank_score);

        return {
            ...source,
            source:
                source.source ||
                source.url ||
                source.title ||
                `Source ${index + 1}`,
            title:
                source.title ||
                source.source ||
                source.url ||
                `Source ${index + 1}`,
            chunk:
                source.chunk ||
                source.content ||
                source.page_content ||
                "",
            chunk_id:
                source.chunk_id ??
                source.id ??
                index + 1,
            distance: Number.isFinite(distance) ? distance : 0,
            rerank_score:
                rerankScore !== null && Number.isFinite(rerankScore)
                    ? rerankScore
                    : null
        };
    });
}

function renderSources(sources) {
    const normalizedSources = normalizeSources(sources);

    return normalizedSources.length > 0
        ? normalizedSources.map(source => {
            const sourceText = source.title || source.source;
            const isUrl = /^https?:\/\//.test(source.source || "");
            const sourceLabel = `
                ${sourceText}
                &middot; chunk ${source.chunk_id}
                &middot; ${source.distance.toFixed(2)}
            `;
            const sourceHeader = isUrl
                ? `
                    <a
                        class="source-link"
                        href="${source.source}"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        ${sourceLabel}
                    </a>
                  `
                : `
                    <strong
                        class="source-link"
                        onclick="loadChunkContent(${source.chunk_id})"
                    >
                        ${sourceLabel}
                    </strong>
                  `;

            return `
                <div class="source-card">
                    ${sourceHeader}
                    <p>${source.chunk}</p>
                </div>
            `;
        }).join("")
        : "<p>No relevant sources found.</p>";
}

function buildKbChatPayload(query) {
    const mode = chatModeSelect.value;
    const settings = getRetrievalSettings();
    const payload = {
        mode,
        query,
        stream: true,
        top_k: settings.top_k,
        score_threshold: settings.score_threshold,
        prompt_name: settings.prompt_name,
        return_direct: settings.return_direct,
        rerank: settings.rerank,
        rerank_top_n: settings.rerank_top_n
    };

    if (mode === "local_kb") {
        payload.kb_name = kbSelector.value || "default";
    }

    if (mode === "temp_kb") {
        payload.temp_kb_id = currentTempKbId;
    }

    if (currentConversationId) {
        payload.conversation_id = currentConversationId;
    }

    return payload;
}

function getRetrievalSettings() {
    return {
        top_k: Number(debugTopKInput.value) || 3,
        score_threshold:
            Number(debugScoreThresholdInput.value) || 0.8,
        prompt_name: debugPromptNameSelect.value || "default",
        return_direct: debugReturnDirectInput.checked,
        rerank: debugRerankInput.checked,
        rerank_top_n: Number(debugRerankTopNInput.value) || 3
    };
}

function buildDebugPayload(query) {
    const payload = buildKbChatPayload(query);
    payload.stream = false;
    payload.return_direct = true;
    return payload;
}

function extractDebugResults(data) {
    if (Array.isArray(data)) return data;
    if (!data) return [];

    if (Array.isArray(data.sources)) return data.sources;
    if (Array.isArray(data.results)) return data.results;
    if (Array.isArray(data.docs)) return data.docs;

    if (data.type === "sources" && Array.isArray(data.sources)) {
        return data.sources;
    }

    return [];
}

function renderDebugResults(results) {
    const debugResultsEl = document.getElementById("debug-results");
    if (!debugResultsEl) return;

    const normalizedResults = normalizeSources(results);

    debugResultsEl.innerHTML = normalizedResults.length > 0
        ? normalizedResults.map(source => {
            const sourceText = source.title || source.source;
            const isUrl = /^https?:\/\//.test(source.source || "");
            const sourceHeader = isUrl
                ? `
                    <a
                        href="${source.source}"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        ${sourceText}
                    </a>
                  `
                : `
                    <strong
                        class="source-link"
                        onclick="loadChunkContent(${source.chunk_id})"
                    >
                        ${sourceText}
                    </strong>
                  `;

            return `
                <div class="debug-result">
                    <div class="debug-result-meta">
                        ${sourceHeader}
                        <span>chunk ${source.chunk_id}</span>
                        <span>distance ${source.distance.toFixed(2)}</span>
                        ${
                            source.rerank_score === null
                                ? ""
                                : `<span>rerank ${source.rerank_score.toFixed(4)}</span>`
                        }
                    </div>
                    <p>${source.chunk}</p>
                </div>
            `;
        }).join("")
        : "<p>No debug results found.</p>";
}

function renderFeedbackControls(messageId) {
    const disabled = messageId ? "" : "disabled";

    return `
        <div class="feedback-controls" data-feedback-status="">
            <button
                type="button"
                class="feedback-like"
                onclick="sendFeedback(this, 1)"
                ${disabled}
            >
                👍 Like
            </button>
            <button
                type="button"
                class="feedback-dislike"
                onclick="sendFeedback(this, -1)"
                ${disabled}
            >
                👎 Dislike
            </button>
            <span class="feedback-status">
                ${messageId ? "" : "Feedback available when answer completes."}
            </span>
        </div>
    `;
}

function setCurrentConversation(conversationId, title = null) {
    currentConversationId = conversationId || null;

    currentConversationLabel.textContent = currentConversationId
        ? title || `Conversation ${currentConversationId}`
        : "New Conversation";

    saveChatHistory();
    highlightCurrentConversation();
}

function highlightCurrentConversation() {
    conversationList
        .querySelectorAll(".conversation-item")
        .forEach(item => {
            item.classList.toggle(
                "active",
                String(item.dataset.conversationId) ===
                    String(currentConversationId)
            );
        });
}

function setMessageFeedbackId(messageEl, messageId) {
    if (!messageId) return;

    messageEl.dataset.assistantMessageId = messageId;
    const controls = messageEl.querySelector(".feedback-controls");

    if (!controls) return;

    controls.querySelectorAll("button").forEach(button => {
        button.disabled = false;
    });

    const status = controls.querySelector(".feedback-status");
    status.textContent = "";
}

async function sendFeedback(button, score) {
    const messageEl = button.closest(".message");
    const messageId = messageEl.dataset.assistantMessageId;

    if (!messageId) {
        showToast("Feedback is not available for this answer yet.", "error");
        return;
    }

    let reason = null;

    if (score === -1) {
        reason = prompt("Why was this answer not helpful?");
    }

    try {
        const response = await fetch(`${API_BASE}/chat/feedback`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message_id: Number(messageId),
                score,
                reason
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast(data.error, "error");
            return;
        }

        const controls =
            messageEl.querySelector(".feedback-controls");
        const status =
            controls.querySelector(".feedback-status");

        controls.dataset.feedbackStatus =
            score === 1 ? "like" : "dislike";

        status.textContent =
            score === 1 ? "Liked" : "Disliked";

        saveChatHistory();
        showToast("Feedback saved.", "success");
    } catch (error) {
        console.error(error);
        showToast("Failed to save feedback.", "error");
    }
}

function renderJsonChatMessage(question, data) {
    const sources = data.sources || [];
    const answer = data.answer || "";
    const answerText =
        answer.includes("insufficient_quota") && sources.length > 0
            ? normalizeSources(sources)[0].chunk
            : answer;

    chatHistoryEl.innerHTML += `
        <div
            class="message"
            data-assistant-message-id="${data.assistant_message_id || ""}"
        >
            <h3 class="user-label">User</h3>
            <p>${question}</p>

            <h3 class="assistant-label">Assistant</h3>
            <p>${answerText}</p>

            ${renderFeedbackControls(data.assistant_message_id)}

            <h3>Sources</h3>
            <div class="sources">${renderSources(sources)}</div>
        </div>
        <hr>
    `;
}

function renderConversationMessages(messages) {
    const entries = [];
    let pendingUser = null;

    for (const message of messages) {
        if (message.role === "user") {
            pendingUser = message;
            continue;
        }

        if (message.role === "assistant") {
            entries.push(`
                <div
                    class="message"
                    data-assistant-message-id="${message.id || ""}"
                >
                    ${
                        pendingUser
                            ? `
                                <h3 class="user-label">User</h3>
                                <p>${pendingUser.content}</p>
                            `
                            : ""
                    }

                    <h3 class="assistant-label">Assistant</h3>
                    <p>${message.content}</p>

                    ${renderFeedbackControls(message.id)}

                    <h3>Sources</h3>
                    <div class="sources">
                        <p>Sources are available for new streamed answers.</p>
                    </div>
                </div>
                <hr>
            `);
            pendingUser = null;
        }
    }

    if (pendingUser) {
        entries.push(`
            <div class="message">
                <h3 class="user-label">User</h3>
                <p>${pendingUser.content}</p>
            </div>
            <hr>
        `);
    }

    chatHistoryEl.innerHTML =
        entries.join("") || "<p>No messages in this conversation yet.</p>";
}

async function handleJsonChatFallback(response, question) {
    const data = await response.json();

    const loadingEl = document.querySelector(".loading");
    if (loadingEl) loadingEl.remove();

    if (data.conversation_id) {
        setCurrentConversation(data.conversation_id);
        loadConversations();
    }

    if (data.return_direct) {
        renderJsonChatMessage(question, {
            answer: "",
            sources: data.sources || [],
            assistant_message_id: null
        });
        saveChatHistory();
        questionInput.value = "";
        return;
    }

    renderJsonChatMessage(question, data);
    saveChatHistory();
    questionInput.value = "";
}

function parseSSEEvent(eventText) {
    const eventData = eventText
        .split("\n")
        .map(line => line.trimEnd())
        .filter(line => line.startsWith("data:"))
        .map(line => line.replace(/^data:\s?/, ""))
        .join("\n")
        .trim();

    if (!eventData || eventData === "[DONE]") return null;

    try {
        const event = JSON.parse(eventData);
        persistConversationId(event.conversation_id);
        return event;
    } catch (error) {
        console.error("Failed to parse SSE event:", eventData, error);
        return null;
    }
}

function persistConversationIdFromText(text) {
    const match = text.match(/"conversation_id"\s*:\s*"?(\d+)"?/);
    if (match) {
        persistConversationId(match[1]);
    }
}

async function readSSE(response, onEvent) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    async function flushEvents(force = false) {
        const normalizedBuffer = buffer.replace(/\r\n/g, "\n");
        const parts = normalizedBuffer.split("\n\n");
        const completeEvents = force ? parts : parts.slice(0, -1);

        buffer = force ? "" : parts[parts.length - 1] || "";

        for (const eventText of completeEvents) {
            const event = parseSSEEvent(eventText);
            if (event) await onEvent(event);
        }
    }

    while (true) {
        const { value, done } = await reader.read();

        if (done) {
            const tail = decoder.decode();
            persistConversationIdFromText(tail);
            buffer += tail;
            await flushEvents(true);
            break;
        }

        const chunk = decoder.decode(value, { stream: true });
        persistConversationIdFromText(chunk);
        buffer += chunk;
        await flushEvents(false);
    }
}

function getTokenContent(event) {
    if (event.type === "token") return event.content || "";
    if (typeof event.answer === "string") return event.answer;

    return event.choices?.[0]?.delta?.content || "";
}

function getCurrentConversationLabel() {
    return (
        currentConversationLabel ||
        document.getElementById("current-conversation-label") ||
        document.getElementById("current-conversation")
    );
}

function persistConversationId(conversationId) {
    if (
        conversationId === undefined ||
        conversationId === null ||
        conversationId === ""
    ) {
        return;
    }
    const conversationIdText = String(conversationId);

    currentConversationId = conversationIdText;
    localStorage.setItem(
        "currentConversationId",
        conversationIdText
    );

    const labelEl = getCurrentConversationLabel();
    if (labelEl) {
        labelEl.textContent = `Conversation ${conversationIdText}`;
    }
}

function persistConversationFromEvent(event, messageEl) {
    const conversationId = event?.conversation_id;
    persistConversationId(conversationId);

    if (messageEl) {
        messageEl.dataset.conversationId =
            currentConversationId || "";
    }

    highlightCurrentConversation();
}

async function readChatStream(
    response,
    messageEl,
    answerEl,
    sourcesEl,
    query
) {
    await readSSE(response, async event => {
        persistConversationFromEvent(event, messageEl);

        if (event.type === "sources" || event.sources || event.docs) {
            sourcesEl.innerHTML =
                renderSources(event.sources || event.docs || []);
            return;
        }

        if (event.type === "error") {
            const errorMessage = event.message || "Streaming failed.";
            answerEl.textContent = errorMessage;
            showToast(errorMessage, "error");

            if (currentConversationId) {
                await loadConversations();
            } else {
                await recoverLatestConversationAfterAsk(query);
            }

            return;
        }

        const tokenContent = getTokenContent(event);
        if (tokenContent) {
            answerEl.textContent += tokenContent;
            return;
        }

        if (event.type === "done") {
            setMessageFeedbackId(
                messageEl,
                event.assistant_message_id
            );
            if (!currentConversationId) {
                await recoverLatestConversationAfterAsk(query);
            }
            await loadConversations();
            questionInput.value = "";
        }
    });

    if (!currentConversationId) {
        await recoverLatestConversationAfterAsk(query);
    }

    await loadConversations();
}

async function ask() {
    const question = questionInput.value.trim();
    if (!question) return;

    if (chatModeSelect.value === "temp_kb" && !currentTempKbId) {
        showToast("Upload a temp file first.", "error");
        return;
    }

    const entryEl = document.createElement("div");
    const messageEl = document.createElement("div");
    messageEl.className = "message loading";
    messageEl.innerHTML = `
        <h3 class="user-label">User</h3>
        <p>${question}</p>

        <h3 class="assistant-label">Assistant</h3>
        <p class="stream-answer"></p>

        ${renderFeedbackControls(null)}

        <h3>Sources</h3>
        <div class="sources">
            <p>Loading sources...</p>
        </div>
    `;

    entryEl.appendChild(messageEl);
    entryEl.appendChild(document.createElement("hr"));
    chatHistoryEl.appendChild(entryEl);

    const answerEl = messageEl.querySelector(".stream-answer");
    const sourcesEl = messageEl.querySelector(".sources");

    try {
        const payload = buildKbChatPayload(question);

        const response = await fetch(`${API_BASE}/kb_chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const contentType = response.headers.get("content-type") || "";

        if (
            !response.body ||
            contentType.includes("application/json")
        ) {
            entryEl.remove();
            await handleJsonChatFallback(response, question);
            return;
        }

        await readChatStream(
            response,
            messageEl,
            answerEl,
            sourcesEl,
            question
        );
        messageEl.classList.remove("loading");
    } catch (error) {
        console.error(error);

        try {
            const response = await fetch(`${API_BASE}/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question,
                    conversation_id: currentConversationId
                })
            });

            entryEl.remove();
            await handleJsonChatFallback(response, question);
        } catch (fallbackError) {
            console.error(fallbackError);
            messageEl.classList.remove("loading");
            answerEl.textContent = "Server error. Please check backend.";
        }
    } finally {
        if (!currentConversationId) {
            await recoverLatestConversationAfterAsk(question);
        }
    }
}

async function debugSearch() {
    const query = questionInput.value.trim();

    if (!query) {
        showToast("Enter a question to debug retrieval.", "error");
        return;
    }

    if (chatModeSelect.value === "temp_kb" && !currentTempKbId) {
        showToast("Upload a temp file first.", "error");
        return;
    }

    debugResults.innerHTML = "<p>Searching...</p>";

    try {
        const response = await fetch(`${API_BASE}/kb_chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(buildDebugPayload(query))
        });

        const data = await response.json();

        if (data.error) {
            debugResults.innerHTML = `<p>${data.error}</p>`;
            return;
        }

        renderDebugResults(extractDebugResults(data));
    } catch (error) {
        console.error(error);
        debugResults.innerHTML = "<p>Debug search failed.</p>";
    }
}

async function readTempFileStream(response) {
    await readSSE(response, async event => {
        if (event.type === "sources" || event.sources || event.docs) {
            tempSources.innerHTML =
                renderSources(event.sources || event.docs || []);
            return;
        }

        const tokenContent = getTokenContent(event);
        if (tokenContent) {
            tempAnswerText.textContent += tokenContent;
        }
    });
}

async function uploadTempFile() {
    const file = tempFileInput.files[0];

    if (!file) {
        showToast("Please choose a temp file first.", "error");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch(`${API_BASE}/temp_upload`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!data.temp_kb_id) {
            showToast(data.message || "Temp upload failed.", "error");
            return;
        }

        currentTempKbId = data.temp_kb_id;
        tempKbIdEl.textContent = currentTempKbId;
        tempAnswerText.textContent = "";
        tempSources.innerHTML = "<p>No temp file question yet.</p>";

        showToast("Temp file uploaded.", "success");
    } catch (error) {
        console.error(error);
        showToast("Temp upload failed. Please check backend.", "error");
    }
}

async function askTempFile() {
    const query = tempQuestionInput.value.trim();

    if (!currentTempKbId) {
        showToast("Upload a temp file first.", "error");
        return;
    }

    if (!query) return;

    tempAnswerText.textContent = "";
    tempSources.innerHTML = "<p>Loading sources...</p>";

    try {
        const response = await fetch(`${API_BASE}/file_chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                query,
                temp_kb_id: currentTempKbId,
                stream: true
            })
        });

        const contentType = response.headers.get("content-type") || "";

        if (!response.body || !contentType.includes("text/event-stream")) {
            const data = await response.json();
            tempAnswerText.textContent = data.answer || data.error || "";
            tempSources.innerHTML = renderSources(data.sources || []);
            return;
        }

        await readTempFileStream(response);
        tempQuestionInput.value = "";
    } catch (error) {
        console.error(error);
        tempAnswerText.textContent =
            "Temp file chat failed. Please check backend.";
        tempSources.innerHTML = "";
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
                <div class="document-main">
                    <strong
                        class="document-name"
                        onclick="toggleFileChunks('${file.filename}')"
                    >
                        ${file.filename}
                    </strong>

                    <div class="document-meta">
                        <span>${file.size} bytes</span>
                        <span>${file.docs_count || 0} chunks</span>
                        <span>
                            chunk ${file.chunk_size || 300}
                            / overlap ${file.chunk_overlap || 50}
                        </span>
                        <span>${file.time}</span>
                    </div>

                    ${
                        file.error
                            ? `<div class="document-error">${file.error}</div>`
                            : ""
                    }
                </div>

                <span class="file-status file-status-${file.status || "indexed"}">
                    ${file.status || "indexed"}
                </span>

                <button
                    type="button"
                    onclick="reindexDocument(${JSON.stringify(file.filename)}, ${file.chunk_size || 300}, ${file.chunk_overlap || 50})"
                >
                    Reindex
                </button>

                <button
                    type="button"
                    onclick="deleteDocument('${file.filename}')"
                >
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

async function reindexDocument(filename, currentChunkSize, currentChunkOverlap) {
    const chunkSizeInput = prompt(
        "chunk_size",
        currentChunkSize || 300
    );

    if (chunkSizeInput === null) return;

    const chunkOverlapInput = prompt(
        "chunk_overlap",
        currentChunkOverlap || 50
    );

    if (chunkOverlapInput === null) return;

    const chunkSize = Number(chunkSizeInput);
    const chunkOverlap = Number(chunkOverlapInput);

    if (!Number.isInteger(chunkSize) || chunkSize <= 0) {
        showToast("chunk_size must be a positive integer.", "error");
        return;
    }

    if (!Number.isInteger(chunkOverlap) || chunkOverlap < 0) {
        showToast("chunk_overlap must be zero or a positive integer.", "error");
        return;
    }

    try {
        const response = await fetch(
            `${API_BASE}/documents/${encodeURIComponent(filename)}/reindex`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    chunk_size: chunkSize,
                    chunk_overlap: chunkOverlap
                })
            }
        );

        const data = await response.json();

        if (data.error) {
            showToast(data.error, "error");
        } else {
            showToast(data.message || "File reindexed.", "success");
        }

        loadStats();
        loadDocuments();
    } catch (error) {
        console.error(error);
        showToast("Reindex failed. Please check backend.", "error");
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

async function exportKb() {
    const kbName = kbSelector.value;

    if (!kbName) {
        showToast("Select a knowledge base first.", "error");
        return;
    }

    try {
        const response = await fetch(
            `${API_BASE}/knowledge_bases/${encodeURIComponent(kbName)}/export`
        );

        if (!response.ok) {
            showToast("Export failed.", "error");
            return;
        }

        const contentType = response.headers.get("content-type") || "";

        if (contentType.includes("application/json")) {
            const data = await response.json();
            showToast(data.error || "Export failed.", "error");
            return;
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${kbName}_export.zip`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);

        showToast("Knowledge base exported.", "success");
    } catch (error) {
        console.error(error);
        showToast("Export failed. Please check backend.", "error");
    }
}

async function importKb() {
    const file = kbImportFileInput.files[0];

    if (!file) {
        showToast("Choose a KB export zip first.", "error");
        return;
    }

    const override = confirm(
        "Override existing KB if the same name already exists?"
    );

    const formData = new FormData();
    formData.append("file", file);
    formData.append("override", override ? "true" : "false");

    try {
        const response = await fetch(`${API_BASE}/knowledge_bases/import`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            showToast(data.error, "error");
            return;
        }

        showToast(
            `Imported ${data.kb_name}: ${data.files_count} files, ${data.chunks_count} chunks.`,
            "success"
        );

        await loadKnowledgeBases();

        if (data.kb_name) {
            kbSelector.value = data.kb_name;
            await switchKnowledgeBase();
        }

        loadStats();
        loadDocuments();
    } catch (error) {
        console.error(error);
        showToast("Import failed. Please check backend.", "error");
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
// 5. Conversation Functions
// =============================

async function recoverLatestConversationAfterAsk(query) {
    try {
        const response = await fetch(`${API_BASE}/conversations`);
        const data = await response.json();
        const conversations = data.conversations || [];

        if (conversations.length === 0) return null;

        const normalizedQuery = (query || "").trim();
        const conversation =
            conversations.find(item => {
                const title = item.title || "";
                return (
                    title === normalizedQuery ||
                    title.includes(normalizedQuery) ||
                    normalizedQuery.includes(title)
                );
            }) ||
            conversations[0];

        if (!conversation) return null;

        persistConversationId(conversation.id);
        await loadConversations();

        return conversation;
    } catch (error) {
        console.error("Failed to recover latest conversation:", error);
        return null;
    }
}

async function loadConversations() {
    try {
        const response = await fetch(`${API_BASE}/conversations`);
        const data = await response.json();
        const conversations = data.conversations || [];

        conversationList.innerHTML = conversations.length > 0
            ? conversations.map(conversation => `
                <button
                    type="button"
                    class="conversation-item"
                    data-conversation-id="${conversation.id}"
                >
                    <span>${conversation.title}</span>
                    <small>${conversation.create_time}</small>
                </button>
            `).join("")
            : "<p>No conversations yet.</p>";

        conversationList
            .querySelectorAll(".conversation-item")
            .forEach((button, index) => {
                const conversation = conversations[index];

                button.addEventListener("click", () => {
                    loadConversation(
                        conversation.id,
                        conversation.title
                    );
                });
            });

        highlightCurrentConversation();
    } catch (error) {
        console.error(error);
        conversationList.innerHTML = "<p>Failed to load conversations.</p>";
    }
}

async function loadConversation(conversationId, title) {
    try {
        const response = await fetch(
            `${API_BASE}/conversations/${conversationId}/messages`
        );
        const data = await response.json();

        setCurrentConversation(conversationId, title);
        renderConversationMessages(data.messages || []);
    } catch (error) {
        console.error(error);
        showToast("Failed to load conversation.", "error");
    }
}

function newConversation() {
    setCurrentConversation(null);
    chatHistoryEl.innerHTML = "";
    questionInput.value = "";
}


// =============================
// 6. Chat History Functions
// =============================

function saveChatHistory() {
    if (currentConversationId) {
        localStorage.setItem(
            "currentConversationId",
            String(currentConversationId)
        );
    } else {
        localStorage.removeItem("currentConversationId");
    }
}

async function restoreChatHistory() {
    await loadConversations();

    const savedConversationId = Number(
        localStorage.getItem("currentConversationId")
    );

    if (savedConversationId) {
        await loadConversation(savedConversationId);
    }
}

function clearChatHistory() {
    localStorage.removeItem("currentConversationId");
    currentConversationId = null;
    currentConversationLabel.textContent = "New Conversation";
    chatHistoryEl.innerHTML = "";
    highlightCurrentConversation();
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

btnSend.addEventListener("click", function (event) {
    event.preventDefault();
    ask();
});

btnUpload.addEventListener("click", function (event) {
    event.preventDefault();
    uploadPdf();
});

btnClear.addEventListener("click", function (event) {
    event.preventDefault();
    clearChatHistory();
});

btnNewConversation.addEventListener("click", function (event) {
    event.preventDefault();
    newConversation();
});

btnDebugSearch.addEventListener("click", function (event) {
    event.preventDefault();
    debugSearch();
});

btnTempUpload.addEventListener("click", function (event) {
    event.preventDefault();
    uploadTempFile();
});

btnTempAsk.addEventListener("click", function (event) {
    event.preventDefault();
    askTempFile();
});

questionInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        event.preventDefault();
        ask();
    }
});

tempQuestionInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        event.preventDefault();
        askTempFile();
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

btnCreateKb.addEventListener("click", function (event) {
    event.preventDefault();
    createKnowledgeBase();
});

btnDeleteKb.addEventListener("click", function (event) {
    event.preventDefault();
    deleteKnowledgeBase();
});

btnExportKb.addEventListener("click", function (event) {
    event.preventDefault();
    exportKb();
});

btnImportKb.addEventListener("click", function (event) {
    event.preventDefault();
    importKb();
});

btnSearchChunks.addEventListener("click", function (event) {
    event.preventDefault();
    searchChunks();
});

// =============================
// 7. Init
// =============================

restoreChatHistory();
loadKnowledgeBases();
document.getElementById("chunk-viewer").innerHTML =
    "Select a chunk to preview its content.";
