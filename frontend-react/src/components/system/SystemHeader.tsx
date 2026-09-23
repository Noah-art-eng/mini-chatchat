import { Activity } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { HealthResponse } from "../../api/system";

type SystemHeaderProps = {
  health: HealthResponse | null;
  status: "loading" | "ready" | "error";
};

/** 用途：负责 SystemHeader 的界面或数据处理职责。 */
export function SystemHeader({ health, status }: SystemHeaderProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <header className="page-header system-hero">
      <div className="page-header-icon" aria-hidden="true">
        <Icon icon={Activity} size="lg" tone="info" />
      </div>
      <div>
        <p className="eyebrow">{t("nav.settings")}</p>
        <h1>{t("settings.title")}</h1>
        <p>{t("settings.subtitle")}</p>
      </div>
      <div className={`system-health-orb system-health-${health?.status || status}`}>
        <span>{t("settings.health")}</span>
        <strong>{health?.status || status}</strong>
      </div>
    </header>
  );
}
