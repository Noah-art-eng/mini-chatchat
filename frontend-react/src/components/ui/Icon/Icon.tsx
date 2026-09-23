import type { HTMLAttributes, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { cx } from "../utils";
import "./Icon.css";

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
      className={cx("ui-icon", `ui-icon--${size}`, `ui-icon--tone-${tone}`, className)}
      {...accessibilityProps}
      {...props}
    >
      {IconSource ? <IconSource aria-hidden="true" strokeWidth={1.8} /> : children}
    </span>
  );
}
