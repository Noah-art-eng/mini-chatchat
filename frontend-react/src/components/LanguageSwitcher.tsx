import { useI18n, type LanguageCode } from "../i18n";

/** 用途：负责 LanguageSwitcher 的界面或数据处理职责。 */
export function LanguageSwitcher() {
  const { language, setLanguage, t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <label className="language-switcher">
      <span>{t("language.label")}</span>
      <select
        aria-label={t("language.label")}
        data-testid="language-switcher"
        onChange={event => setLanguage(event.target.value as LanguageCode)}
        value={language}
      >
        <option value="en">{t("language.english")}</option>
        <option value="zh-CN">{t("language.chinese")}</option>
      </select>
    </label>
  );
}
