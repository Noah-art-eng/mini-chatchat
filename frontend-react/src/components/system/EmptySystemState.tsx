import { useI18n } from "../../i18n";

/** 用途：负责 EmptySystemState 的界面或数据处理职责。 */
export function EmptySystemState() {
  const { t } = useI18n();

  return <p className="muted">{t("settings.loading")}</p>;
}
