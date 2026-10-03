import { SquareTerminal } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { HealthResponse, ModelsResponse } from "../../api/system";
import { systemBadgeClassName, systemCardClassName } from "./systemStyles";

type RuntimeInfoProps = {
  health: HealthResponse | null;
  models: ModelsResponse | null;
};

export function RuntimeInfo({ health, models }: RuntimeInfoProps) {
  const { t } = useI18n();

  return (
    <article className={`${systemCardClassName} system-wide-card col-span-full`}>
      <span className={systemBadgeClassName}>{t("settings.readonly")}</span>
      <h2><Icon icon={SquareTerminal} size="sm" tone="system" />{t("settings.runtime")}</h2>
      <dl>
        <div>
          <dt>{t("settings.version")}</dt>
          <dd>{health?.version || t("common.unavailable")}</dd>
        </div>
        <div>
          <dt>{t("settings.modelProvider")}</dt>
          <dd>{models?.chat.provider || health?.provider || t("common.unavailable")}</dd>
        </div>
        <div>
          <dt>{t("settings.noSave")}</dt>
          <dd>{t("settings.readonly")}</dd>
        </div>
      </dl>
    </article>
  );
}
