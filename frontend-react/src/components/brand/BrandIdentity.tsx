import { BrandLogo } from "./BrandLogo";
import { useI18n } from "../../i18n";

type BrandIdentityProps = {
  mode?: "expanded" | "compact" | "mobile" | "iconOnly";
  onGoHome?: () => void;
};

/** 用途：负责 BrandIdentity 的界面或数据处理职责。 */
export function BrandIdentity({
  mode = "expanded",
  onGoHome
}: BrandIdentityProps) {
  const { t } = useI18n();
  const isIconOnly = mode === "iconOnly" || mode === "compact";

  if (onGoHome) {
    /** 用途：负责 return 的界面或数据处理职责。 */
    return (
      <button
        aria-label={t("app.goToChat")}
        className={`brand-identity brand-identity--${mode}`}
        onClick={onGoHome}
        type="button"
      >
        <BrandLogo size={40} title="" />
        {!isIconOnly && (
          <span className="brand-copy">
            <strong>{t("app.name")}</strong>
            <small>{t("app.tagline")}</small>
          </span>
        )}
      </button>
    );
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className={`brand-identity brand-identity--${mode}`}>
      <BrandLogo size={40} title={t("app.name")} />
      {!isIconOnly && (
        <span className="brand-copy">
          <strong>{t("app.name")}</strong>
          <small>{t("app.tagline")}</small>
        </span>
      )}
    </div>
  );
}
