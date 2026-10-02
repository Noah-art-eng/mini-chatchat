import type { HTMLAttributes, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { cx } from "../utils";

type IconSize = "sm" | "md" | "lg";
type IconTone =
  | "default"
  | "muted"
  | "brand"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "file"
  | "knowledge"
  | "database"
  | "browser"
  | "mcp"
  | "system";

type IconProps = {
  ariaLabel?: string;
  children?: ReactNode;
  decorative?: boolean;
  icon?: LucideIcon;
  label?: string;
  size?: IconSize;
  tone?: IconTone;
} & HTMLAttributes<HTMLSpanElement>;

const sizeClasses: Record<IconSize, string> = {
  sm: "h-[var(--icon-size-sm)] w-[var(--icon-size-sm)]",
  md: "h-[var(--icon-size-md)] w-[var(--icon-size-md)]",
  lg: "h-[var(--icon-size-lg)] w-[var(--icon-size-lg)]",
};

const toneClasses: Record<IconTone, string> = {
  default: "text-current",
  muted: "text-mc-muted",
  brand: "text-mc-brand",
  success: "text-mc-success",
  warning: "text-mc-warning",
  danger: "text-mc-danger",
  info: "text-mc-info",
  file: "text-mc-success",
  knowledge: "text-[var(--icon-tone-knowledge)]",
  database: "text-mc-info",
  browser: "text-[var(--icon-tone-browser)]",
  mcp: "text-[var(--icon-tone-mcp)]",
  system: "text-mc-warning",
};

/** 用途：负责 Icon 的界面或数据处理职责。 */
export function Icon({
  ariaLabel,
  children,
  className,
  decorative = true,
  icon: IconSource,
  label,
  size = "md",
  tone = "default",
  ...props
}: IconProps) {
  const accessibilityProps = decorative
    ? { "aria-hidden": true }
    : { "aria-label": ariaLabel || label, role: "img" };

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <span
      className={cx(
        "ui-icon inline-flex flex-none items-center justify-center leading-none [&_svg]:block [&_svg]:h-full [&_svg]:w-full",
        sizeClasses[size],
        toneClasses[tone],
        className
      )}
      {...accessibilityProps}
      {...props}
    >
      {IconSource ? <IconSource aria-hidden="true" strokeWidth={1.8} /> : children}
    </span>
  );
}
