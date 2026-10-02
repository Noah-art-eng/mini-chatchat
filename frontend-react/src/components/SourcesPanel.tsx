import { FileSearch, FileText, Globe2 } from "lucide-react";
import { useI18n } from "../i18n";
import { useConversationStore } from "../stores/conversationStore";
import { Icon } from "./ui";
import { contextStyles } from "./ContextPanel/contextStyles";

/** 用途：负责 SourcesPanel 的界面或数据处理职责。 */
export function SourcesPanel() {
  const { t } = useI18n();
  const { messages, selectedAssistantMessageId, sources } =
    /** 用途：负责 useConversationStore 的界面或数据处理职责。 */
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

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <section
      aria-label="Sources"
      className={contextStyles.panelSection}
      data-testid="sources-panel"
      id="sources-panel"
    >
      <p className="eyebrow">{t("sources.title")}</p>
      <h2 className={contextStyles.panelTitle}>{selectedMessage ? t("sources.messageSources") : t("sources.latestSources")}</h2>

      {showHistoricalMissing && (
        <p className="muted">{t("sources.missing")}</p>
      )}

      {!showHistoricalMissing && visibleSources.length === 0 && (
        <div className={contextStyles.empty}>
          <Icon icon={FileSearch} size="lg" tone="muted" />
          <p className="muted">{t("sources.empty")}</p>
        </div>
      )}

      <div className={contextStyles.list}>
        {visibleSources.map((source, index) => {
          const label =
            source.title ||
            source.file_name ||
            source.url ||
            source.source ||
            /** 用途：负责 t 的界面或数据处理职责。 */
            t("sources.source", { index: index + 1 });
          const sourceUrl = source.url || source.source || "";
          const isUrl = /^https?:\/\//.test(sourceUrl);
          const preview = source.chunk || source.content || t("sources.noPreview");

          /** 用途：负责 return 的界面或数据处理职责。 */
          return (
            <article className={contextStyles.card} key={`${label}-${index}`}>
              <span className={contextStyles.sourceIndex}>
                <Icon icon={isUrl ? Globe2 : FileText} size="sm" tone={isUrl ? "browser" : "file"} />
                {String(index + 1).padStart(2, "0")}
              </span>
              <div className={contextStyles.sourceMeta}>
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
              </div>
              {isUrl && (
                <strong className={contextStyles.sourceTitle} data-testid="source-title">
                  {source.title || label}
                </strong>
              )}
              <p className={contextStyles.sourcePreview} data-testid="source-preview">{preview}</p>
              {isUrl && (
                <a
                  className={contextStyles.sourceLink}
                  href={sourceUrl}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  {t("sources.openSource")}
                </a>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
