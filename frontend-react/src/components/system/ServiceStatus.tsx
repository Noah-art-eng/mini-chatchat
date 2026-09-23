import { LanguageSwitcher } from "../LanguageSwitcher";
import { useI18n } from "../../i18n";
import type { HealthResponse } from "../../api/system";

type ServiceStatusProps = {
  health: HealthResponse | null;
};

/** 用途：负责 ServiceStatus 的界面或数据处理职责。 */
export function ServiceStatus({ health }: ServiceStatusProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
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
