import { useConversationStore } from "../stores/conversationStore";

export function SourcesPanel() {
  const { messages, selectedAssistantMessageId, sources } =
    useConversationStore();
  const selectedMessage = messages.find(
    message =>
      message.role === "assistant" && message.id === selectedAssistantMessageId
  );
  const selectedMessageSources =
    selectedMessage?.sources || selectedMessage?.metadata?.sources || [];
  const visibleSources = selectedMessage ? selectedMessageSources : sources;
  const showHistoricalMissing =
    selectedMessage && selectedMessageSources.length === 0;

  return (
    <section
      aria-label="Sources"
      className="sources-panel"
      data-testid="sources-panel"
      id="sources-panel"
    >
      <p className="eyebrow">Sources / KB Panel</p>
      <h2>{selectedMessage ? "Message Sources" : "Latest Sources"}</h2>

      {showHistoricalMissing && (
        <p className="muted">Historical sources were not saved.</p>
      )}

      {!showHistoricalMissing && visibleSources.length === 0 && (
        <p className="muted">
          Sources from the current streamed answer will appear here. KB
          management and retrieval debug migrate in later phases.
        </p>
      )}

      <div className="source-list">
        {visibleSources.map((source, index) => {
          const label =
            source.title ||
            source.file_name ||
            source.url ||
            source.source ||
            `Source ${index + 1}`;
          const sourceUrl = source.url || source.source || "";
          const isUrl = /^https?:\/\//.test(sourceUrl);
          const scores = [
            typeof source.score === "number"
              ? `score ${source.score.toFixed(2)}`
              : null,
            typeof source.distance === "number"
              ? `distance ${source.distance.toFixed(2)}`
              : null,
            typeof source.rerank_score === "number"
              ? `rerank ${source.rerank_score.toFixed(2)}`
              : null
          ].filter(Boolean);

          return (
            <article className="source-card" key={`${label}-${index}`}>
              <div className="source-meta">
                {isUrl ? (
                  <a
                    data-testid="source-url"
                    href={sourceUrl}
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
              {isUrl && (
                <strong className="source-title" data-testid="source-title">
                  {source.title || label}
                </strong>
              )}
              <p data-testid="source-preview">
                {source.chunk || source.content || "No source preview available."}
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
