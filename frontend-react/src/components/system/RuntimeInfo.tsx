import { SquareTerminal } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { HealthResponse, ModelsResponse } from "../../api/system";

type RuntimeInfoProps = {
  health: HealthResponse | null;
  models: ModelsResponse | null;
};

/** 用途：负责 RuntimeInfo 的界面或数据处理职责。 */
export function RuntimeInfo({ health, models }: RuntimeInfoProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article className="settings-card system-wide-card">
      <span className="settings-badge">{t("settings.readonly")}</span>
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
