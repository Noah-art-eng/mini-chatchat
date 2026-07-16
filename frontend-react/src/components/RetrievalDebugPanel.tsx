import { useMemo, useState } from "react";
import { debugKbChat } from "../api/chat";
import { useConversationStore } from "../stores/conversationStore";
import type { KBChatRequest } from "../types/chat";
import type { Source } from "../types/conversation";

function getSourceLabel(source: Source, index: number) {
  return (
    source.title ||
    source.file_name ||
    source.url ||
    source.source ||
    `Source ${index + 1}`
  );
}

function getSourceHref(source: Source) {
  const value = source.url || source.source || "";
  return /^https?:\/\//.test(value) ? value : null;
}

function getPreview(source: Source) {
  return source.chunk || source.content || "No preview text returned.";
}

function getScores(source: Source) {
  return [
    typeof source.score === "number" ? `score ${source.score.toFixed(2)}` : null,
    typeof source.distance === "number"
      ? `distance ${source.distance.toFixed(2)}`
      : null,
    typeof source.rerank_score === "number"
      ? `rerank ${source.rerank_score.toFixed(2)}`
      : null
  ].filter(Boolean);
}

export function RetrievalDebugPanel() {
  const { chatMode, kbName, tempKbId } = useConversationStore();
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(3);
  const [scoreThreshold, setScoreThreshold] = useState(0.8);
  const [promptName, setPromptName] = useState("default");
  const [returnDirect, setReturnDirect] = useState(true);
  const [rerank, setRerank] = useState(false);
  const [rerankTopN, setRerankTopN] = useState(3);
  const [results, setResults] = useState<Source[]>([]);
  const [status, setStatus] = useState<
    "idle" | "loading" | "success" | "error" | "empty"
  >("idle");
  const [error, setError] = useState<string | null>(null);

  const debugPayload = useMemo<KBChatRequest>(() => {
    const retrievalMode = chatMode === "agent" ? "local_kb" : chatMode;
    const payload: KBChatRequest = {
      mode: retrievalMode,
      query: query.trim(),
      stream: false,
      top_k: topK,
      score_threshold: scoreThreshold,
      prompt_name: promptName || "default",
      return_direct: returnDirect,
      rerank,
      rerank_top_n: rerankTopN
    };

    if (retrievalMode === "local_kb") {
      payload.kb_name = kbName;
    }

    if (retrievalMode === "temp_kb" && tempKbId) {
      payload.temp_kb_id = tempKbId;
    }

    return payload;
  }, [
    chatMode,
    kbName,
    promptName,
    query,
    rerank,
    rerankTopN,
    returnDirect,
    scoreThreshold,
    tempKbId,
    topK
  ]);

  async function runDebugSearch() {
    if (!debugPayload.query) {
      setStatus("error");
      setError("Enter a debug query first.");
      setResults([]);
      return;
    }

    if (chatMode === "temp_kb" && !tempKbId) {
      setStatus("error");
      setError("Please upload a temp file first.");
      setResults([]);
      return;
    }

    setStatus("loading");
    setError(null);
    setResults([]);

    try {
      const response = await debugKbChat(debugPayload);

      if (response.error) {
        setStatus("error");
        setError(response.error);
        return;
      }

      const nextResults =
        response.sources || response.results || response.docs || [];
      setResults(nextResults);
      setStatus(nextResults.length > 0 ? "success" : "empty");
    } catch (debugError) {
      setStatus("error");
      setError(
        debugError instanceof Error ? debugError.message : "Debug search failed."
      );
    }
  }

  return (
    <section
      aria-label="Retrieval debug"
      className="retrieval-debug-panel"
      data-testid="retrieval-debug-panel"
    >
      <div className="panel-heading">
        <p className="eyebrow">Retrieval Debug</p>
        <h2>Search Probe</h2>
      </div>

      <label className="debug-field">
        Debug query
        <input
          data-testid="debug-query-input"
          onChange={event => setQuery(event.target.value)}
          placeholder="Test retrieval without changing chat"
          value={query}
        />
      </label>

      <div className="debug-grid">
        <label className="debug-field">
          top_k
          <input
            data-testid="debug-top-k-input"
            min={1}
            onChange={event => setTopK(Number(event.target.value) || 1)}
            type="number"
            value={topK}
          />
        </label>

        <label className="debug-field">
          threshold
          <input
            data-testid="debug-score-threshold-input"
            onChange={event =>
              setScoreThreshold(Number(event.target.value) || 0)
            }
            step={0.01}
            type="number"
            value={scoreThreshold}
          />
        </label>
      </div>

      <label className="debug-field">
        prompt_name
        <input
          data-testid="debug-prompt-name-input"
          onChange={event => setPromptName(event.target.value)}
          value={promptName}
        />
      </label>

      <div className="debug-checks">
        <label>
          <input
            checked={returnDirect}
            data-testid="debug-return-direct-checkbox"
            onChange={event => setReturnDirect(event.target.checked)}
            type="checkbox"
          />
          return_direct
        </label>
        <label>
          <input
            checked={rerank}
            data-testid="debug-rerank-checkbox"
            onChange={event => setRerank(event.target.checked)}
            type="checkbox"
          />
          rerank
        </label>
      </div>

      <label className="debug-field">
        rerank_top_n
        <input
          data-testid="debug-rerank-top-n-input"
          min={1}
          onChange={event => setRerankTopN(Number(event.target.value) || 1)}
          type="number"
          value={rerankTopN}
        />
      </label>

      <button
        className="debug-search-button"
        data-testid="debug-search-button"
        disabled={status === "loading"}
        onClick={() => {
          void runDebugSearch();
        }}
        type="button"
      >
        {status === "loading" ? "Searching" : "Debug Search"}
      </button>

      <div className="debug-results" data-testid="debug-results">
        {status === "idle" && (
          <p className="muted">Run a debug search to inspect retrieval results.</p>
        )}
        {status === "loading" && <p className="muted">Loading debug results...</p>}
        {status === "empty" && <p className="muted">No debug results found.</p>}
        {status === "error" && (
          <p className="inline-error">{error || "Debug search failed."}</p>
        )}

        {results.map((source, index) => {
          const label = getSourceLabel(source, index);
          const href = getSourceHref(source);
          const scores = getScores(source);

          return (
            <article className="debug-result-card" key={`${label}-${index}`}>
              <div className="source-meta">
                {href ? (
                  <a
                    data-testid="source-url"
                    href={href}
                    rel="noopener noreferrer"
                    target="_blank"
                  >
                    {label}
                  </a>
                ) : (
                  <strong data-testid="source-title">{label}</strong>
                )}
                <small>
                  chunk {source.chunk_id ?? index + 1}
                  {scores.length > 0 ? ` · ${scores.join(" · ")}` : ""}
                </small>
              </div>
              {href && (
                <strong className="source-title" data-testid="source-title">
                  {source.title || label}
                </strong>
              )}
              <p data-testid="source-preview">{getPreview(source)}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
