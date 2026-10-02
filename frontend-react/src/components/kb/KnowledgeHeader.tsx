import { Library } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";

/** 用途：负责 KnowledgeHeader 的界面或数据处理职责。 */
export function KnowledgeHeader() {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <header className="page-header knowledge-header mb-[18px] grid min-w-[0] grid-cols-[auto_minmax(0,1fr)] items-start gap-[14px] [&_h1]:m-[0] [&_p]:mb-[0] [&_p]:max-w-[760px] [&_p]:leading-[1.55]">
      <div className="inline-flex h-[var(--icon-container-lg)] w-[var(--icon-container-lg)] flex-none items-center justify-center rounded-mc-lg border border-mc-border-subtle bg-mc-brand-soft text-mc-brand" aria-hidden="true">
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
