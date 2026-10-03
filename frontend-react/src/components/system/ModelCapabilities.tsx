import { useI18n } from "../../i18n";
import type { ModelsResponse } from "../../api/system";
import { systemBadgeClassName, systemCardClassName } from "./systemStyles";

type ModelCapabilitiesProps = {
  kbName: string;
  models: ModelsResponse | null;
};

export function ModelCapabilities({ kbName, models }: ModelCapabilitiesProps) {
  const { t } = useI18n();

  return (
    <article className={systemCardClassName}>
      <span className={`${systemBadgeClassName} status-ok`}>
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
