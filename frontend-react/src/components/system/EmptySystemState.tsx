import { useI18n } from "../../i18n";

export function EmptySystemState() {
  const { t } = useI18n();

  return <p className="muted">{t("settings.loading")}</p>;
}
