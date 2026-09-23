import { Cpu } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { ModelsResponse } from "../../api/system";
import type { ChatMode } from "../../types/chat";

type ModelCardProps = {
  chatMode: ChatMode;
  models: ModelsResponse | null;
};

/** 用途：负责 ModelCard 的界面或数据处理职责。 */
export function ModelCard({ chatMode, models }: ModelCardProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article className="settings-card">
      <span className="settings-badge provider-badge">
        {models?.chat.provider || t("common.loading")}
      </span>
      <h2><Icon icon={Cpu} size="sm" tone="brand" />{t("settings.model")}</h2>
      <dl>
        <div>
          <dt>{t("settings.modelProvider")}</dt>
          <dd>{models?.chat.provider || t("common.unavailable")}</dd>
        </div>
        <div>
          <dt>{t("settings.chatModel")}</dt>
          <dd>{models?.chat.default_model || t("common.unavailable")}</dd>
        </div>
        <div>
          <dt>{t("settings.baseUrl")}</dt>
          <dd>{models?.chat.base_url || t("common.unavailable")}</dd>
        </div>
        <div>
          <dt>{t("app.currentMode")}</dt>
          <dd>{t(`modes.${chatMode}`)}</dd>
        </div>
      </dl>
    </article>
  );
}
