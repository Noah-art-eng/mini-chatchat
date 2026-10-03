import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Spinner } from "../Spinner";
import { cx, type UiSize } from "../utils";

type ButtonVariant = "primary" | "secondary" | "ghost" | "outline" | "danger" | "quiet";

type ButtonProps = {
  leadingIcon?: ReactNode;
  loading?: boolean;
  size?: UiSize;
  trailingIcon?: ReactNode;
  variant?: ButtonVariant;
} & ButtonHTMLAttributes<HTMLButtonElement>;

const sizeClasses: Record<UiSize, string> = {
  sm: "min-h-[var(--control-height-sm)] px-mc-3",
  md: "min-h-[var(--control-height-md)] px-mc-4",
  lg: "min-h-[var(--control-height-lg)] px-mc-5",
};

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-mc-brand text-mc-inverse enabled:hover:bg-mc-brand-hover enabled:active:bg-mc-brand-active",
  secondary:
    "border-mc-border bg-mc-surface text-mc-text enabled:hover:border-mc-border-strong enabled:hover:bg-mc-hover",
  outline:
    "border-mc-border bg-mc-surface text-mc-text enabled:hover:border-mc-border-strong enabled:hover:bg-mc-hover",
  ghost:
    "bg-transparent text-mc-secondary enabled:hover:bg-mc-hover enabled:hover:text-mc-text",
  quiet:
    "bg-transparent text-mc-secondary enabled:hover:bg-mc-hover enabled:hover:text-mc-text",
  danger:
    "bg-mc-danger text-mc-inverse enabled:hover:bg-mc-danger enabled:hover:brightness-[.96]",
};

export function Button({
  children,
  className,
  disabled,
  leadingIcon,
  loading = false,
  size = "md",
  trailingIcon,
  type = "button",
  variant = "secondary",
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      className={cx(
        "relative inline-flex min-w-max items-center justify-center gap-mc-2 rounded-mc-md border border-solid border-transparent font-mc-sans text-mc-body-small font-mc-semibold tracking-[0] transition-[background-color,border-color,color,box-shadow] duration-[var(--motion-duration-fast)] ease-[var(--motion-ease-standard)] focus-visible:[outline-width:var(--focus-ring-width)] focus-visible:[outline-style:solid] focus-visible:[outline-color:var(--color-border-focus)] focus-visible:outline-offset-[var(--focus-ring-offset)] focus-visible:[box-shadow:var(--shadow-focus)] disabled:cursor-not-allowed disabled:opacity-[.56]",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      disabled={isDisabled}
      type={type}
      {...props}
    >
      {loading && <Spinner ariaLabel="Loading" size="sm" />}
      {!loading && leadingIcon && (
        <span className="inline-flex flex-none items-center" aria-hidden="true">
          {leadingIcon}
        </span>
      )}
      <span className="inline-flex items-center">{children}</span>
      {!loading && trailingIcon && (
        <span className="inline-flex flex-none items-center" aria-hidden="true">
          {trailingIcon}
        </span>
      )}
    </button>
  );
}
