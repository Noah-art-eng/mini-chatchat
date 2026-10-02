import { useI18n } from "../../i18n";
import { cx } from "../ui/utils";
import { kbPlainControlClassName } from "./kbStyles";

type KnowledgeToolbarProps = {
  isDeveloperMode: boolean;
  isLoading: boolean;
  onOpenDebug: () => void;
  onOpenDetails: () => void;
  onRefreshDocuments: () => void;
  onToggleDeveloperMode: () => void;
};

/** 用途：负责 KnowledgeToolbar 的界面或数据处理职责。 */
export function KnowledgeToolbar({
  isDeveloperMode,
  isLoading,
  onOpenDebug,
  onOpenDetails,
  onRefreshDocuments,
  onToggleDeveloperMode
}: KnowledgeToolbarProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="knowledge-toolbar flex items-center justify-end gap-mc-2 [grid-area:toolbar]">
      <button className={kbPlainControlClassName} onClick={onOpenDetails} type="button">
        {t("kb.viewDetails")}
      </button>
      <button
        className={`${kbPlainControlClassName} refresh-documents-button rounded-mc-pill border-0 bg-mc-surface px-mc-3 py-[9px] font-[700] text-mc-text [box-shadow:none] hover:bg-mc-hover`}
        data-testid="refresh-documents-button"
        disabled={isLoading}
        onClick={onRefreshDocuments}
        type="button"
      >
        {t("kb.refresh")}
      </button>
      <button
        aria-pressed={isDeveloperMode}
        className={cx(kbPlainControlClassName, "developer-toggle", isDeveloperMode && "active")}
        onClick={onToggleDeveloperMode}
        type="button"
      >
        {t("chat.developerMode")}
      </button>
      {isDeveloperMode && (
        <button className={kbPlainControlClassName} onClick={onOpenDebug} type="button">
          {t("kb.debugTab")}
        </button>
      )}
    </div>
  );
}
