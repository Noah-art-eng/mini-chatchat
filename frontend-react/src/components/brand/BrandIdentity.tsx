import { BrandLogo } from "./BrandLogo";
import { useI18n } from "../../i18n";
import { cx } from "../ui/utils";

const baseClass = "brand-identity flex min-h-[var(--control-height-lg)] w-full min-w-[0] items-center gap-mc-3 rounded-mc-lg border border-transparent bg-transparent p-mc-1 text-left text-mc-text transition-[background,border-color] duration-[var(--motion-duration-fast)]";
const buttonClass = "cursor-pointer hover:border-mc-border-subtle hover:bg-mc-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mc-border-focus";

type BrandIdentityProps = {
  mode?: "expanded" | "compact" | "mobile" | "iconOnly";
  onGoHome?: () => void;
};

export function BrandIdentity({
  mode = "expanded",
  onGoHome
}: BrandIdentityProps) {
  const { t } = useI18n();
  const isIconOnly = mode === "iconOnly" || mode === "compact";

  if (onGoHome) {
    return (
      <button
        aria-label={t("app.goToChat")}
        className={cx(baseClass, `brand-identity--${mode}`, buttonClass)}
        onClick={onGoHome}
        type="button"
      >
        <BrandLogo size={40} title="" />
        {!isIconOnly && (
          <span className="brand-copy grid min-w-[0] gap-px">
            <strong className="overflow-hidden text-ellipsis whitespace-nowrap text-mc-body-small font-mc-semibold leading-[var(--line-height-compact)] text-mc-text">{t("app.name")}</strong>
            <small className="overflow-hidden text-ellipsis text-mc-caption leading-[var(--line-height-compact)] text-mc-muted">{t("app.tagline")}</small>
          </span>
        )}
      </button>
    );
  }

  return (
    <div className={cx(baseClass, `brand-identity--${mode}`)}>
      <BrandLogo size={40} title={t("app.name")} />
      {!isIconOnly && (
        <span className="brand-copy grid min-w-[0] gap-px">
          <strong className="overflow-hidden text-ellipsis whitespace-nowrap text-mc-body-small font-mc-semibold leading-[var(--line-height-compact)] text-mc-text">{t("app.name")}</strong>
          <small className="overflow-hidden text-ellipsis text-mc-caption leading-[var(--line-height-compact)] text-mc-muted">{t("app.tagline")}</small>
        </span>
      )}
    </div>
  );
}
