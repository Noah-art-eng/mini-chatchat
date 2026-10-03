import { Activity, CircleAlert, CircleCheck } from "lucide-react";
import { ServiceStatus } from "./ServiceStatus";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { HealthResponse } from "../../api/system";
import { systemBadgeClassName, systemCardClassName } from "./systemStyles";

type HealthCardProps = {
  health: HealthResponse | null;
  status: "loading" | "ready" | "error";
};

export function HealthCard({ health, status }: HealthCardProps) {
  const { t } = useI18n();
  const isOk = (health?.status || status) === "ok" || status === "ready";

  return (
    <article className={systemCardClassName}>
      <span className={`${systemBadgeClassName} status-${health?.status || status}`}>
        <Icon icon={isOk ? CircleCheck : CircleAlert} size="sm" tone={isOk ? "success" : "warning"} />
        {health?.status || status}
      </span>
      <h2><Icon icon={Activity} size="sm" tone="info" />{t("settings.general")}</h2>
      <ServiceStatus health={health} />
    </article>
  );
}
