import { useI18n } from "../../i18n";
import type { KnowledgeBase } from "../../types/kb";

type KnowledgeBaseListProps = {
  currentKb: string;
  isLoading: boolean;
  knowledgeBases: KnowledgeBase[];
  onSelectKnowledgeBase: (kbName: string) => void;
};

/** 用途：负责 KnowledgeBaseList 的界面或数据处理职责。 */
export function KnowledgeBaseList({
  currentKb,
  isLoading,
  knowledgeBases,
  onSelectKnowledgeBase
}: KnowledgeBaseListProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <>
      <div className="kb-list" data-testid="kb-list">
        {knowledgeBases.map(kb => (
          <button
            className={kb.kb_name === currentKb ? "kb-option active" : "kb-option"}
            data-testid={`kb-option-${kb.kb_name}`}
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

      <label className="kb-selector">
        {t("kb.quickSelect")}
        <select
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
