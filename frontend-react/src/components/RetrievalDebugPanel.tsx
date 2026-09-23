import { useMemo, useState } from "react";
import { debugKbChat } from "../api/chat";
import { useI18n } from "../i18n";
import { useConversationStore } from "../stores/conversationStore";
import type { KBChatRequest } from "../types/chat";
import type { Source } from "../types/conversation";

/** 用途：负责 getSourceLabel 的界面或数据处理职责。 */
function getSourceLabel(source: Source, index: number) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    source.title ||
    source.file_name ||
    source.url ||
    source.source ||
    `Source ${index + 1}`
  );
}

/** 用途：负责 getSourceHref 的界面或数据处理职责。 */
function getSourceHref(source: Source) {
  const value = source.url || source.source || "";
  return /^https?:\/\//.test(value) ? value : null;
}

/** 用途：负责 getPreview 的界面或数据处理职责。 */
function getPreview(source: Source) {
  return source.chunk || source.content || "";
}

/** 用途：负责 getScores 的界面或数据处理职责。 */
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

/** 用途：负责 RetrievalDebugPanel 的界面或数据处理职责。 */
export function RetrievalDebugPanel() {
  const { t } = useI18n();
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

  /** 用途：负责 runDebugSearch 的界面或数据处理职责。 */
  async function runDebugSearch() {
    if (!debugPayload.query) {
      /** 用途：负责 setStatus 的界面或数据处理职责。 */
      setStatus("error");
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(t("debug.enterQuery"));
      /** 用途：负责 setResults 的界面或数据处理职责。 */
      setResults([]);
      return;
    }

    if (chatMode === "temp_kb" && !tempKbId) {
      /** 用途：负责 setStatus 的界面或数据处理职责。 */
      setStatus("error");
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(t("debug.uploadTempFirst"));
      /** 用途：负责 setResults 的界面或数据处理职责。 */
      setResults([]);
      return;
    }

    /** 用途：负责 setStatus 的界面或数据处理职责。 */
    setStatus("loading");
    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);
    /** 用途：负责 setResults 的界面或数据处理职责。 */
    setResults([]);

    try {
      const response = await debugKbChat(debugPayload);

      if (response.error) {
        /** 用途：负责 setStatus 的界面或数据处理职责。 */
        setStatus("error");
        /** 用途：负责 setError 的界面或数据处理职责。 */
        setError(response.error);
        return;
      }

      const nextResults =
        response.sources || response.results || response.docs || [];
      /** 用途：负责 setResults 的界面或数据处理职责。 */
      setResults(nextResults);
      /** 用途：负责 setStatus 的界面或数据处理职责。 */
      setStatus(nextResults.length > 0 ? "success" : "empty");
    } catch (debugError) {
      /** 用途：负责 setStatus 的界面或数据处理职责。 */
      setStatus("error");
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(
        debugError instanceof Error ? debugError.message : t("debug.failed")
      );
    }
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <section
      aria-label={t("debug.title")}
      className="retrieval-debug-panel"
      data-testid="retrieval-debug-panel"
    >
      <div className="panel-heading">
        <p className="eyebrow">{t("chat.developerTools")}</p>
        <h2>{t("debug.subtitle")}</h2>
        <p>{t("debug.description")}</p>
      </div>

      <label className="debug-field">
        {t("debug.query")}
        <input
          data-testid="debug-query-input"
          onChange={event => setQuery(event.target.value)}
          placeholder={t("debug.queryPlaceholder")}
          value={query}
        />
      </label>

      <div className="debug-grid">
        <label className="debug-field">
          {t("debug.topK")}
          <input
            data-testid="debug-top-k-input"
            min={1}
            onChange={event => setTopK(Number(event.target.value) || 1)}
            type="number"
            value={topK}
          />
        </label>

        <label className="debug-field">
          {t("debug.threshold")}
          <input
            data-testid="debug-score-threshold-input"
            onChange={event =>
              /** 用途：负责 setScoreThreshold 的界面或数据处理职责。 */
              setScoreThreshold(Number(event.target.value) || 0)
            }
            step={0.01}
            type="number"
            value={scoreThreshold}
          />
        </label>
      </div>

      <label className="debug-field">
        {t("debug.promptName")}
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
          {t("debug.returnDirect")}
        </label>
        <label>
          <input
            checked={rerank}
            data-testid="debug-rerank-checkbox"
            onChange={event => setRerank(event.target.checked)}
            type="checkbox"
          />
          {t("debug.rerank")}
        </label>
      </div>

      <label className="debug-field">
        {t("debug.rerankTopN")}
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
        {status === "loading" ? t("debug.searching") : t("debug.run")}
      </button>

      <div className="debug-results" data-testid="debug-results">
        {status === "idle" && (
          <p className="muted">{t("debug.idle")}</p>
        )}
        {status === "loading" && <p className="muted">{t("debug.loading")}</p>}
        {status === "empty" && <p className="muted">{t("debug.empty")}</p>}
        {status === "error" && (
          <p className="inline-error">{error || t("debug.failed")}</p>
        )}

        {results.map((source, index) => {
          const label = getSourceLabel(source, index);
          const href = getSourceHref(source);
          const scores = getScores(source);

          /** 用途：负责 return 的界面或数据处理职责。 */
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
              <p data-testid="source-preview">
                {getPreview(source) || t("debug.noPreview")}
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
