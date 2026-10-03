import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Spinner } from "../Spinner";
import { cx, type UiSize } from "../utils";

type IconButtonVariant = "ghost" | "secondary" | "danger";

type IconButtonProps = {
  "aria-label": string;
  children: ReactNode;
  loading?: boolean;
  size?: UiSize;
  variant?: IconButtonVariant;
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children">;

const sizeClasses: Record<UiSize, string> = {
  sm: "h-[var(--control-height-sm)] w-[var(--control-height-sm)]",
  md: "h-[var(--control-height-md)] w-[var(--control-height-md)]",
  lg: "h-[var(--control-height-lg)] w-[var(--control-height-lg)]",
};

const variantClasses: Record<IconButtonVariant, string> = {
  ghost: "bg-transparent",
  secondary: "border-mc-border bg-mc-surface",
  danger:
    "bg-mc-danger-soft text-mc-danger enabled:hover:bg-mc-danger enabled:hover:text-mc-inverse",
};

export function IconButton({
  children,
  className,
  disabled,
  loading = false,
  size = "md",
  type = "button",
  variant = "ghost",
  ...props
}: IconButtonProps) {
  return (
    <button
      className={cx(
        "ui-icon-button inline-flex items-center justify-center rounded-mc-sm border border-solid border-transparent text-mc-secondary transition-[background-color,border-color,color,box-shadow] duration-[var(--motion-duration-fast)] ease-[var(--motion-ease-standard)] enabled:hover:border-mc-border-strong enabled:hover:bg-mc-hover enabled:hover:text-mc-text focus-visible:[outline-width:var(--focus-ring-width)] focus-visible:[outline-style:solid] focus-visible:[outline-color:var(--color-border-focus)] focus-visible:outline-offset-[var(--focus-ring-offset)] focus-visible:[box-shadow:var(--shadow-focus)] disabled:cursor-not-allowed disabled:opacity-[.56]",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      disabled={disabled || loading}
      type={type}
      {...props}
    >
      {loading ? <Spinner ariaLabel="Loading" size="sm" /> : children}
    </button>
  );
}
