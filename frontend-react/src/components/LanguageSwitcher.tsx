import { useI18n, type LanguageCode } from "../i18n";

export function LanguageSwitcher() {
  const { language, setLanguage, t } = useI18n();

  return (
    <label className="flex min-w-max items-center gap-mc-2 text-mc-caption font-mc-bold text-mc-secondary">
      <span>{t("language.label")}</span>
      <select
        aria-label={t("language.label")}
        className="min-h-[34px] min-w-[132px] py-[5px] pr-[28px] pl-mc-2"
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
