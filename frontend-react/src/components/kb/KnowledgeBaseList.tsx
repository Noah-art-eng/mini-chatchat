import { useI18n } from "../../i18n";
import { cx } from "../ui/utils";
import type { KnowledgeBase } from "../../types/kb";

type KnowledgeBaseListProps = {
  currentKb: string;
  isLoading: boolean;
  knowledgeBases: KnowledgeBase[];
  onSelectKnowledgeBase: (kbName: string) => void;
};

export function KnowledgeBaseList({
  currentKb,
  isLoading,
  knowledgeBases,
  onSelectKnowledgeBase
}: KnowledgeBaseListProps) {
  const { t } = useI18n();

  return (
    <>
      <div className="kb-list flex max-h-[280px] min-w-0 flex-col gap-mc-2 overflow-y-auto [grid-area:list] max-[900px]:grid max-[900px]:grid-cols-[repeat(auto-fit,minmax(180px,1fr))]" data-testid="kb-list">
        {knowledgeBases.map(kb => (
          <button
            className={cx(
              "kb-option grid min-w-0 gap-[3px] rounded-[16px] border border-solid px-mc-3 py-[10px] text-left transition-[background-color,border-color,transform] duration-[140ms] ease-[ease] hover:-translate-y-px hover:border-mc-border-strong [&>small]:overflow-hidden [&>small]:text-ellipsis [&>small]:whitespace-nowrap [&>small]:text-mc-muted [&>span]:overflow-hidden [&>span]:text-ellipsis [&>span]:whitespace-nowrap",
              kb.kb_name === currentKb
                ? "active border-mc-border-subtle bg-mc-brand-soft text-[var(--color-brand-active)] [box-shadow:none]"
                : "border-mc-border bg-mc-surface text-mc-text"
            )}
            data-testid={`kb-option-${kb.kb_name}`}
            disabled={isLoading}
            key={kb.kb_name}
            onClick={() => onSelectKnowledgeBase(kb.kb_name)}
            type="button"
          >
            <span>{kb.kb_name}</span>
            {kb.embed_model && <small>{kb.embed_model}</small>}
          </button>
        ))}
      </div>

      {knowledgeBases.length === 0 && !isLoading && (
        <p className="muted">{t("kb.emptyKbs")}</p>
      )}

      <label className="kb-selector grid min-w-0 gap-mc-2 [grid-area:select]">
        {t("kb.quickSelect")}
        <select
          disabled={isLoading}
          onChange={event => onSelectKnowledgeBase(event.target.value)}
          value={currentKb}
        >
          {knowledgeBases.map(kb => (
            <option key={kb.kb_name} value={kb.kb_name}>
              {kb.kb_name}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}
