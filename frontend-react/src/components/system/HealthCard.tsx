import { Activity, CircleAlert, CircleCheck } from "lucide-react";
import { ServiceStatus } from "./ServiceStatus";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { HealthResponse } from "../../api/system";

type HealthCardProps = {
  health: HealthResponse | null;
  status: "loading" | "ready" | "error";
};

/** 用途：负责 HealthCard 的界面或数据处理职责。 */
export function HealthCard({ health, status }: HealthCardProps) {
  const { t } = useI18n();
  const isOk = (health?.status || status) === "ok" || status === "ready";

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article className="settings-card">
      <span className={`settings-badge status-${health?.status || status}`}>
        <Icon icon={isOk ? CircleCheck : CircleAlert} size="sm" tone={isOk ? "success" : "warning"} />
        {health?.status || status}
      </span>
      <h2><Icon icon={Activity} size="sm" tone="info" />{t("settings.general")}</h2>
      <ServiceStatus health={health} />
    </article>
  );
}
