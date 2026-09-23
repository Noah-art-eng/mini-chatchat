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

/** 用途：负责 normalizeSources 的界面或数据处理职责。 */
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

/** 用途：负责 renderSources 的界面或数据处理职责。 */
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

/** 用途：负责 buildKbChatPayload 的界面或数据处理职责。 */
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

/** 用途：负责 getRetrievalSettings 的界面或数据处理职责。 */
function getRetrievalSettings() {
    return {
        top_k: Number(debugTopKInput.value) || 3,
        score_threshold:
            /** 用途：负责 Number 的界面或数据处理职责。 */
            Number(debugScoreThresholdInput.value) || 0.8,
        prompt_name: debugPromptNameSelect.value || "default",
        return_direct: debugReturnDirectInput.checked,
        rerank: debugRerankInput.checked,
        rerank_top_n: Number(debugRerankTopNInput.value) || 3
    };
}

/** 用途：负责 buildDebugPayload 的界面或数据处理职责。 */
function buildDebugPayload(query) {
    const payload = buildKbChatPayload(query);
    payload.stream = false;
    payload.return_direct = true;
    return payload;
}

/** 用途：负责 extractDebugResults 的界面或数据处理职责。 */
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

/** 用途：负责 renderDebugResults 的界面或数据处理职责。 */
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

/** 用途：负责 renderFeedbackControls 的界面或数据处理职责。 */
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

/** 用途：负责 setCurrentConversation 的界面或数据处理职责。 */
function setCurrentConversation(conversationId, title = null) {
    currentConversationId = conversationId || null;

    currentConversationLabel.textContent = currentConversationId
        ? title || `Conversation ${currentConversationId}`
        : "New Conversation";

    /** 用途：负责 saveChatHistory 的界面或数据处理职责。 */
    saveChatHistory();
    /** 用途：负责 highlightCurrentConversation 的界面或数据处理职责。 */
    highlightCurrentConversation();
}

/** 用途：负责 highlightCurrentConversation 的界面或数据处理职责。 */
function highlightCurrentConversation() {
    conversationList
        .querySelectorAll(".conversation-item")
        .forEach(item => {
            item.classList.toggle(
                "active",
                /** 用途：负责 String 的界面或数据处理职责。 */
                String(item.dataset.conversationId) ===
                    /** 用途：负责 String 的界面或数据处理职责。 */
                    String(currentConversationId)
            );
        });
}

/** 用途：负责 setMessageFeedbackId 的界面或数据处理职责。 */
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

/** 用途：负责 sendFeedback 的界面或数据处理职责。 */
async function sendFeedback(button, score) {
    const messageEl = button.closest(".message");
    const messageId = messageEl.dataset.assistantMessageId;

    if (!messageId) {
        /** 用途：负责 showToast 的界面或数据处理职责。 */
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
            /** 用途：负责 showToast 的界面或数据处理职责。 */
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

        /** 用途：负责 saveChatHistory 的界面或数据处理职责。 */
        saveChatHistory();
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast("Feedback saved.", "success");
    } catch (error) {
        console.error(error);
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast("Failed to save feedback.", "error");
    }
}

/** 用途：负责 renderJsonChatMessage 的界面或数据处理职责。 */
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

/** 用途：负责 renderConversationMessages 的界面或数据处理职责。 */
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

/** 用途：负责 handleJsonChatFallback 的界面或数据处理职责。 */
async function handleJsonChatFallback(response, question) {
    const data = await response.json();

    const loadingEl = document.querySelector(".loading");
    if (loadingEl) loadingEl.remove();

    if (data.conversation_id) {
        /** 用途：负责 setCurrentConversation 的界面或数据处理职责。 */
        setCurrentConversation(data.conversation_id);
        /** 用途：负责 loadConversations 的界面或数据处理职责。 */
        loadConversations();
    }

    if (data.return_direct) {
        /** 用途：负责 renderJsonChatMessage 的界面或数据处理职责。 */
        renderJsonChatMessage(question, {
            answer: "",
            sources: data.sources || [],
            assistant_message_id: null
        });
        /** 用途：负责 saveChatHistory 的界面或数据处理职责。 */
        saveChatHistory();
        questionInput.value = "";
        return;
    }

    /** 用途：负责 renderJsonChatMessage 的界面或数据处理职责。 */
    renderJsonChatMessage(question, data);
    /** 用途：负责 saveChatHistory 的界面或数据处理职责。 */
    saveChatHistory();
    questionInput.value = "";
}

/** 用途：负责 parseSSEEvent 的界面或数据处理职责。 */
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
        /** 用途：负责 persistConversationId 的界面或数据处理职责。 */
        persistConversationId(event.conversation_id);
        return event;
    } catch (error) {
        console.error("Failed to parse SSE event:", eventData, error);
        return null;
    }
}

/** 用途：负责 persistConversationIdFromText 的界面或数据处理职责。 */
function persistConversationIdFromText(text) {
    const match = text.match(/"conversation_id"\s*:\s*"?(\d+)"?/);
    if (match) {
        /** 用途：负责 persistConversationId 的界面或数据处理职责。 */
        persistConversationId(match[1]);
    }
}

/** 用途：负责 readSSE 的界面或数据处理职责。 */
async function readSSE(response, onEvent) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    /** 用途：负责 flushEvents 的界面或数据处理职责。 */
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
            /** 用途：负责 persistConversationIdFromText 的界面或数据处理职责。 */
            persistConversationIdFromText(tail);
            buffer += tail;
            await flushEvents(true);
            break;
        }

        const chunk = decoder.decode(value, { stream: true });
        /** 用途：负责 persistConversationIdFromText 的界面或数据处理职责。 */
        persistConversationIdFromText(chunk);
        buffer += chunk;
        await flushEvents(false);
    }
}

/** 用途：负责 getTokenContent 的界面或数据处理职责。 */
function getTokenContent(event) {
    if (event.type === "token") return event.content || "";
    if (typeof event.answer === "string") return event.answer;

    return event.choices?.[0]?.delta?.content || "";
}

/** 用途：负责 getCurrentConversationLabel 的界面或数据处理职责。 */
function getCurrentConversationLabel() {
    /** 用途：负责 return 的界面或数据处理职责。 */
    return (
        currentConversationLabel ||
        document.getElementById("current-conversation-label") ||
        document.getElementById("current-conversation")
    );
}

/** 用途：负责 persistConversationId 的界面或数据处理职责。 */
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

/** 用途：负责 persistConversationFromEvent 的界面或数据处理职责。 */
function persistConversationFromEvent(event, messageEl) {
    const conversationId = event?.conversation_id;
    /** 用途：负责 persistConversationId 的界面或数据处理职责。 */
    persistConversationId(conversationId);

    if (messageEl) {
        messageEl.dataset.conversationId =
            currentConversationId || "";
    }

    /** 用途：负责 highlightCurrentConversation 的界面或数据处理职责。 */
    highlightCurrentConversation();
}

/** 用途：负责 readChatStream 的界面或数据处理职责。 */
async function readChatStream(
    response,
    messageEl,
    answerEl,
    sourcesEl,
    query
) {
    await readSSE(response, async event => {
        /** 用途：负责 persistConversationFromEvent 的界面或数据处理职责。 */
        persistConversationFromEvent(event, messageEl);

        if (event.type === "sources" || event.sources || event.docs) {
            sourcesEl.innerHTML =
                /** 用途：负责 renderSources 的界面或数据处理职责。 */
                renderSources(event.sources || event.docs || []);
            return;
        }

        if (event.type === "error") {
            const errorMessage = event.message || "Streaming failed.";
            answerEl.textContent = errorMessage;
            /** 用途：负责 showToast 的界面或数据处理职责。 */
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
            /** 用途：负责 setMessageFeedbackId 的界面或数据处理职责。 */
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

/** 用途：负责 ask 的界面或数据处理职责。 */
async function ask() {
    const question = questionInput.value.trim();
    if (!question) return;

    if (chatModeSelect.value === "temp_kb" && !currentTempKbId) {
        /** 用途：负责 showToast 的界面或数据处理职责。 */
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

/** 用途：负责 debugSearch 的界面或数据处理职责。 */
async function debugSearch() {
    const query = questionInput.value.trim();

    if (!query) {
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast("Enter a question to debug retrieval.", "error");
        return;
    }

    if (chatModeSelect.value === "temp_kb" && !currentTempKbId) {
        /** 用途：负责 showToast 的界面或数据处理职责。 */
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

        /** 用途：负责 renderDebugResults 的界面或数据处理职责。 */
        renderDebugResults(extractDebugResults(data));
    } catch (error) {
        console.error(error);
        debugResults.innerHTML = "<p>Debug search failed.</p>";
    }
}

/** 用途：负责 readTempFileStream 的界面或数据处理职责。 */
async function readTempFileStream(response) {
    await readSSE(response, async event => {
        if (event.type === "sources" || event.sources || event.docs) {
            tempSources.innerHTML =
                /** 用途：负责 renderSources 的界面或数据处理职责。 */
                renderSources(event.sources || event.docs || []);
            return;
        }

        const tokenContent = getTokenContent(event);
        if (tokenContent) {
            tempAnswerText.textContent += tokenContent;
        }
    });
}

/** 用途：负责 uploadTempFile 的界面或数据处理职责。 */
async function uploadTempFile() {
    const file = tempFileInput.files[0];

    if (!file) {
        /** 用途：负责 showToast 的界面或数据处理职责。 */
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
            /** 用途：负责 showToast 的界面或数据处理职责。 */
            showToast(data.message || "Temp upload failed.", "error");
            return;
        }

        currentTempKbId = data.temp_kb_id;
        tempKbIdEl.textContent = currentTempKbId;
        tempAnswerText.textContent = "";
        tempSources.innerHTML = "<p>No temp file question yet.</p>";

        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast("Temp file uploaded.", "success");
    } catch (error) {
        console.error(error);
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast("Temp upload failed. Please check backend.", "error");
    }
}

/** 用途：负责 askTempFile 的界面或数据处理职责。 */
async function askTempFile() {
    const query = tempQuestionInput.value.trim();

    if (!currentTempKbId) {
        /** 用途：负责 showToast 的界面或数据处理职责。 */
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

/** 用途：负责 uploadFiles 的界面或数据处理职责。 */
async function uploadFiles(files) {
    if (!files || files.length === 0) {
        /** 用途：负责 alert 的界面或数据处理职责。 */
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

        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast("Files uploaded successfully", "success");

        /** 用途：负责 loadStats 的界面或数据处理职责。 */
        loadStats();
        /** 用途：负责 loadDocuments 的界面或数据处理职责。 */
        loadDocuments();
    } catch (error) {
        console.error(error);
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast("Upload failed. Please check backend.", "error");
    }
}

/** 用途：负责 uploadPdf 的界面或数据处理职责。 */
async function uploadPdf() {
    const files = document.getElementById("pdfFile").files;
    await uploadFiles(files);
}


// =============================
// 4. Knowledge Base Functions
// =============================

/** 用途：负责 loadStats 的界面或数据处理职责。 */
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

/** 用途：负责 loadDocuments 的界面或数据处理职责。 */
async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE}/documents`);
        const data = await response.json();

        allDocuments = data.files;
        /** 用途：负责 renderDocuments 的界面或数据处理职责。 */
        renderDocuments(allDocuments);
    } catch (error) {
        console.error(error);
    }
}

/** 用途：负责 renderDocuments 的界面或数据处理职责。 */
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

/** 用途：负责 toggleFileChunks 的界面或数据处理职责。 */
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
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast(
            "Failed to load chunks.",
            "error"
        );
    }
}

/** 用途：负责 loadChunkContent 的界面或数据处理职责。 */
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
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast(
            "Failed to load chunk content.",
            "error"
        );
    }
}

/** 用途：负责 deleteDocument 的界面或数据处理职责。 */
async function deleteDocument(filename) {
    const confirmed = confirm(`Delete ${filename}?`);
    if (!confirmed) return;

    try {
        const response = await fetch(
            `${API_BASE}/documents/${encodeURIComponent(filename)}`,
            { method: "DELETE" }
        );

        const data = await response.json();
        /** 用途：负责 alert 的界面或数据处理职责。 */
        alert(data.message);

        /** 用途：负责 loadStats 的界面或数据处理职责。 */
        loadStats();
        /** 用途：负责 loadDocuments 的界面或数据处理职责。 */
        loadDocuments();
    } catch (error) {
        console.error(error);
        /** 用途：负责 alert 的界面或数据处理职责。 */
        alert("Delete failed. Please check backend.");
    }
}

/** 用途：负责 reindexDocument 的界面或数据处理职责。 */
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
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast("chunk_size must be a positive integer.", "error");
        return;
    }

    if (!Number.isInteger(chunkOverlap) || chunkOverlap < 0) {
        /** 用途：负责 showToast 的界面或数据处理职责。 */
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
            /** 用途：负责 showToast 的界面或数据处理职责。 */
            showToast(data.error, "error");
        } else {
            /** 用途：负责 showToast 的界面或数据处理职责。 */
            showToast(data.message || "File reindexed.", "success");
        }

        /** 用途：负责 loadStats 的界面或数据处理职责。 */
        loadStats();
        /** 用途：负责 loadDocuments 的界面或数据处理职责。 */
        loadDocuments();
    } catch (error) {
        console.error(error);
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast("Reindex failed. Please check backend.", "error");
    }
}

/** 用途：负责 createKnowledgeBase 的界面或数据处理职责。 */
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

    /** 用途：负责 showToast 的界面或数据处理职责。 */
    showToast("Knowledge base created.", "success");
}

/** 用途：负责 deleteKnowledgeBase 的界面或数据处理职责。 */
async function deleteKnowledgeBase() {
    const kbName = kbSelector.value;

    if (!kbName) return;

    if (kbName === "default") {
        /** 用途：负责 showToast 的界面或数据处理职责。 */
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
            /** 用途：负责 showToast 的界面或数据处理职责。 */
            showToast(data.error, "error");
            return;
        }

        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast(data.message, "success");

        await loadKnowledgeBases();

        kbSelector.value = "default";
        await switchKnowledgeBase();

        document.getElementById("chunk-viewer").innerHTML =
            "Select a chunk to preview its content.";

    } catch (error) {
        console.error(error);
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast(
            "Failed to delete knowledge base.",
            "error"
        );
    }
}

/** 用途：负责 exportKb 的界面或数据处理职责。 */
async function exportKb() {
    const kbName = kbSelector.value;

    if (!kbName) {
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast("Select a knowledge base first.", "error");
        return;
    }

    try {
        const response = await fetch(
            `${API_BASE}/knowledge_bases/${encodeURIComponent(kbName)}/export`
        );

        if (!response.ok) {
            /** 用途：负责 showToast 的界面或数据处理职责。 */
            showToast("Export failed.", "error");
            return;
        }

        const contentType = response.headers.get("content-type") || "";

        if (contentType.includes("application/json")) {
            const data = await response.json();
            /** 用途：负责 showToast 的界面或数据处理职责。 */
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

        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast("Knowledge base exported.", "success");
    } catch (error) {
        console.error(error);
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast("Export failed. Please check backend.", "error");
    }
}

/** 用途：负责 importKb 的界面或数据处理职责。 */
async function importKb() {
    const file = kbImportFileInput.files[0];

    if (!file) {
        /** 用途：负责 showToast 的界面或数据处理职责。 */
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
            /** 用途：负责 showToast 的界面或数据处理职责。 */
            showToast(data.error, "error");
            return;
        }

        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast(
            `Imported ${data.kb_name}: ${data.files_count} files, ${data.chunks_count} chunks.`,
            "success"
        );

        await loadKnowledgeBases();

        if (data.kb_name) {
            kbSelector.value = data.kb_name;
            await switchKnowledgeBase();
        }

        /** 用途：负责 loadStats 的界面或数据处理职责。 */
        loadStats();
        /** 用途：负责 loadDocuments 的界面或数据处理职责。 */
        loadDocuments();
    } catch (error) {
        console.error(error);
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast("Import failed. Please check backend.", "error");
    }
}

/** 用途：负责 searchChunks 的界面或数据处理职责。 */
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

/** 用途：负责 recoverLatestConversationAfterAsk 的界面或数据处理职责。 */
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
                /** 用途：负责 return 的界面或数据处理职责。 */
                return (
                    title === normalizedQuery ||
                    title.includes(normalizedQuery) ||
                    normalizedQuery.includes(title)
                );
            }) ||
            conversations[0];

        if (!conversation) return null;

        /** 用途：负责 persistConversationId 的界面或数据处理职责。 */
        persistConversationId(conversation.id);
        await loadConversations();

        return conversation;
    } catch (error) {
        console.error("Failed to recover latest conversation:", error);
        return null;
    }
}

/** 用途：负责 loadConversations 的界面或数据处理职责。 */
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
                    /** 用途：负责 loadConversation 的界面或数据处理职责。 */
                    loadConversation(
                        conversation.id,
                        conversation.title
                    );
                });
            });

        /** 用途：负责 highlightCurrentConversation 的界面或数据处理职责。 */
        highlightCurrentConversation();
    } catch (error) {
        console.error(error);
        conversationList.innerHTML = "<p>Failed to load conversations.</p>";
    }
}

/** 用途：负责 loadConversation 的界面或数据处理职责。 */
async function loadConversation(conversationId, title) {
    try {
        const response = await fetch(
            `${API_BASE}/conversations/${conversationId}/messages`
        );
        const data = await response.json();

        /** 用途：负责 setCurrentConversation 的界面或数据处理职责。 */
        setCurrentConversation(conversationId, title);
        /** 用途：负责 renderConversationMessages 的界面或数据处理职责。 */
        renderConversationMessages(data.messages || []);
    } catch (error) {
        console.error(error);
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast("Failed to load conversation.", "error");
    }
}

/** 用途：负责 newConversation 的界面或数据处理职责。 */
function newConversation() {
    /** 用途：负责 setCurrentConversation 的界面或数据处理职责。 */
    setCurrentConversation(null);
    chatHistoryEl.innerHTML = "";
    questionInput.value = "";
}


// =============================
// 6. Chat History Functions
// =============================

/** 用途：负责 saveChatHistory 的界面或数据处理职责。 */
function saveChatHistory() {
    if (currentConversationId) {
        localStorage.setItem(
            "currentConversationId",
            /** 用途：负责 String 的界面或数据处理职责。 */
            String(currentConversationId)
        );
    } else {
        localStorage.removeItem("currentConversationId");
    }
}

/** 用途：负责 restoreChatHistory 的界面或数据处理职责。 */
async function restoreChatHistory() {
    await loadConversations();

    const savedConversationId = Number(
        localStorage.getItem("currentConversationId")
    );

    if (savedConversationId) {
        await loadConversation(savedConversationId);
    }
}

/** 用途：负责 clearChatHistory 的界面或数据处理职责。 */
function clearChatHistory() {
    localStorage.removeItem("currentConversationId");
    currentConversationId = null;
    currentConversationLabel.textContent = "New Conversation";
    chatHistoryEl.innerHTML = "";
    /** 用途：负责 highlightCurrentConversation 的界面或数据处理职责。 */
    highlightCurrentConversation();
}

/** 用途：负责 showToast 的界面或数据处理职责。 */
function showToast(message, type = "success") {
    const toastContainer =
        document.getElementById("toast-container");

    const toast = document.createElement("div");

    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    toastContainer.appendChild(toast);

    /** 用途：负责 setTimeout 的界面或数据处理职责。 */
    setTimeout(function () {
        toast.classList.add("hide");

        /** 用途：负责 setTimeout 的界面或数据处理职责。 */
        setTimeout(function () {
            toast.remove();
        }, 300);
    }, 3000);
}

/** 用途：负责 loadKnowledgeBases 的界面或数据处理职责。 */
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

/** 用途：负责 switchKnowledgeBase 的界面或数据处理职责。 */
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

    /** 用途：负责 loadStats 的界面或数据处理职责。 */
    loadStats();
    /** 用途：负责 loadDocuments 的界面或数据处理职责。 */
    loadDocuments();
}


// =============================
// 6. Event Listeners
// =============================

btnSend.addEventListener("click", function (event) {
    event.preventDefault();
    /** 用途：负责 ask 的界面或数据处理职责。 */
    ask();
});

btnUpload.addEventListener("click", function (event) {
    event.preventDefault();
    /** 用途：负责 uploadPdf 的界面或数据处理职责。 */
    uploadPdf();
});

btnClear.addEventListener("click", function (event) {
    event.preventDefault();
    /** 用途：负责 clearChatHistory 的界面或数据处理职责。 */
    clearChatHistory();
});

btnNewConversation.addEventListener("click", function (event) {
    event.preventDefault();
    /** 用途：负责 newConversation 的界面或数据处理职责。 */
    newConversation();
});

btnDebugSearch.addEventListener("click", function (event) {
    event.preventDefault();
    /** 用途：负责 debugSearch 的界面或数据处理职责。 */
    debugSearch();
});

btnTempUpload.addEventListener("click", function (event) {
    event.preventDefault();
    /** 用途：负责 uploadTempFile 的界面或数据处理职责。 */
    uploadTempFile();
});

btnTempAsk.addEventListener("click", function (event) {
    event.preventDefault();
    /** 用途：负责 askTempFile 的界面或数据处理职责。 */
    askTempFile();
});

questionInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        event.preventDefault();
        /** 用途：负责 ask 的界面或数据处理职责。 */
        ask();
    }
});

tempQuestionInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        event.preventDefault();
        /** 用途：负责 askTempFile 的界面或数据处理职责。 */
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
    /** 用途：负责 uploadFiles 的界面或数据处理职责。 */
    uploadFiles(event.dataTransfer.files);
});

documentSearch.addEventListener("input", function () {
    const keyword = documentSearch.value.toLowerCase();
    const filtered = allDocuments.filter(file =>
        file.filename.toLowerCase().includes(keyword)
    );
    /** 用途：负责 renderDocuments 的界面或数据处理职责。 */
    renderDocuments(filtered);
});

kbSelector.addEventListener("change", switchKnowledgeBase);

btnCreateKb.addEventListener("click", function (event) {
    event.preventDefault();
    /** 用途：负责 createKnowledgeBase 的界面或数据处理职责。 */
    createKnowledgeBase();
});

btnDeleteKb.addEventListener("click", function (event) {
    event.preventDefault();
    /** 用途：负责 deleteKnowledgeBase 的界面或数据处理职责。 */
    deleteKnowledgeBase();
});

btnExportKb.addEventListener("click", function (event) {
    event.preventDefault();
    /** 用途：负责 exportKb 的界面或数据处理职责。 */
    exportKb();
});

btnImportKb.addEventListener("click", function (event) {
    event.preventDefault();
    /** 用途：负责 importKb 的界面或数据处理职责。 */
    importKb();
});

btnSearchChunks.addEventListener("click", function (event) {
    event.preventDefault();
    /** 用途：负责 searchChunks 的界面或数据处理职责。 */
    searchChunks();
});

// =============================
// 7. Init
// =============================

restoreChatHistory();
loadKnowledgeBases();
document.getElementById("chunk-viewer").innerHTML =
    "Select a chunk to preview its content.";
