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
    <div className="source-reference-list grid gap-mc-2 text-mc-caption text-mc-muted" aria-label={t("sources.messageSources")}>
      <button
        aria-expanded={isExpanded}
        className="source-reference-toggle inline-flex min-h-[var(--control-height-sm)] cursor-pointer items-center gap-mc-2 justify-self-start rounded-mc-pill border border-mc-border-subtle bg-mc-subtle px-mc-3 text-mc-caption font-mc-semibold text-mc-secondary transition-[background,border-color] duration-[var(--motion-duration-fast)] hover:border-mc-border-strong hover:bg-mc-hover hover:text-mc-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mc-border-focus"
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
        <div className="source-reference-preview grid gap-mc-2">
          {sources.slice(0, 3).map((source, index) => (
            <button
              className="grid cursor-pointer gap-mc-1 rounded-mc-md border border-mc-border-subtle bg-mc-subtle p-mc-3 text-left text-mc-secondary hover:border-mc-border-strong hover:bg-mc-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mc-border-focus [&_strong]:overflow-hidden [&_strong]:text-ellipsis [&_strong]:whitespace-nowrap [&_strong]:text-mc-body-small [&_strong]:text-mc-text [&_span]:text-mc-caption"
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
