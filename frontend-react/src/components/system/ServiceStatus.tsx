import { LanguageSwitcher } from "../LanguageSwitcher";
import { useI18n } from "../../i18n";
import type { HealthResponse } from "../../api/system";

type ServiceStatusProps = {
  health: HealthResponse | null;
};

export function ServiceStatus({ health }: ServiceStatusProps) {
  const { t } = useI18n();

  return (
    <dl>
      <div>
        <dt>{t("settings.service")}</dt>
        <dd>{health?.service || t("common.unavailable")}</dd>
      </div>
      <div>
        <dt>{t("settings.version")}</dt>
        <dd>{health?.version || t("common.unavailable")}</dd>
      </div>
      <div>
        <dt>{t("settings.language")}</dt>
        <dd>
          <LanguageSwitcher />
        </dd>
      </div>
    </dl>
  );
}
