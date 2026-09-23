import { useI18n } from "../../i18n";
import type { ModelsResponse } from "../../api/system";

type ModelCapabilitiesProps = {
  kbName: string;
  models: ModelsResponse | null;
};

/** 用途：负责 ModelCapabilities 的界面或数据处理职责。 */
export function ModelCapabilities({ kbName, models }: ModelCapabilitiesProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article className="settings-card">
      <span className="settings-badge status-ok">
        {models?.embedding.default_model ? "ok" : t("common.loading")}
      </span>
      <h2>{t("settings.retrieval")}</h2>
      <dl>
        <div>
          <dt>{t("app.currentKb")}</dt>
          <dd>{kbName}</dd>
        </div>
        <div>
          <dt>{t("settings.embedding")}</dt>
          <dd>{models?.embedding.default_model || t("common.unavailable")}</dd>
        </div>
      </dl>
    </article>
  );
}
