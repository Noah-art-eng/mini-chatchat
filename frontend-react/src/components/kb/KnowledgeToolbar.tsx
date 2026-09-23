import { useI18n } from "../../i18n";

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
    <div className="knowledge-toolbar">
      <button onClick={onOpenDetails} type="button">
        {t("kb.viewDetails")}
      </button>
      <button
        className="refresh-documents-button"
        data-testid="refresh-documents-button"
        disabled={isLoading}
        onClick={onRefreshDocuments}
        type="button"
      >
        {t("kb.refresh")}
      </button>
      <button
        aria-pressed={isDeveloperMode}
        className={isDeveloperMode ? "developer-toggle active" : "developer-toggle"}
        onClick={onToggleDeveloperMode}
        type="button"
      >
        {t("chat.developerMode")}
      </button>
      {isDeveloperMode && (
        <button onClick={onOpenDebug} type="button">
          {t("kb.debugTab")}
        </button>
      )}
    </div>
  );
}
