import { useState } from "react";
import { useI18n } from "../../i18n";
import type { Source } from "../../types/conversation";

type SourceReferenceListProps = {
  onOpenSources: () => void;
  sources: Source[];
};

/** 用途：负责 sourceLabel 的界面或数据处理职责。 */
function sourceLabel(source: Source, index: number) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    source.title ||
    source.file_name ||
    source.source ||
    source.url ||
    `Source ${index + 1}`
  );
}

/** 用途：负责 SourceReferenceList 的界面或数据处理职责。 */
export function SourceReferenceList({
  onOpenSources,
  sources
}: SourceReferenceListProps) {
  const { t } = useI18n();
  const [isExpanded, setIsExpanded] = useState(false);

  if (sources.length === 0) {
    return null;
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="source-reference-list" aria-label={t("sources.messageSources")}>
      <button
        aria-expanded={isExpanded}
        className="source-reference-toggle"
        onClick={event => {
          event.stopPropagation();
          /** 用途：负责 setIsExpanded 的界面或数据处理职责。 */
          setIsExpanded(current => !current);
          /** 用途：负责 onOpenSources 的界面或数据处理职责。 */
          onOpenSources();
        }}
        type="button"
      >
        <span>{t("sources.messageSourcesWithCount", { count: sources.length })}</span>
        <span aria-hidden="true">{isExpanded ? "−" : "+"}</span>
      </button>
      {isExpanded && (
        <div className="source-reference-preview">
          {sources.slice(0, 3).map((source, index) => (
            <button
              key={`${sourceLabel(source, index)}-${source.chunk_id ?? index}`}
              onClick={event => {
                event.stopPropagation();
                /** 用途：负责 onOpenSources 的界面或数据处理职责。 */
                onOpenSources();
              }}
              title={sourceLabel(source, index)}
              type="button"
            >
              <strong>[{String(index + 1).padStart(2, "0")}] {sourceLabel(source, index)}</strong>
              <span>{source.chunk || source.content || t("sources.noPreview")}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
