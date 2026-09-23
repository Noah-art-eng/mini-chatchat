import { Library } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";

/** 用途：负责 KnowledgeHeader 的界面或数据处理职责。 */
export function KnowledgeHeader() {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <header className="page-header knowledge-header">
      <div className="page-header-icon" aria-hidden="true">
        <Icon icon={Library} size="lg" tone="knowledge" />
      </div>
      <div>
        <p className="eyebrow">{t("nav.knowledgeBase")}</p>
        <h1>{t("kb.title")}</h1>
        <p>{t("kb.subtitle")}</p>
      </div>
    </header>
  );
}
