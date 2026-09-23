import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Spinner } from "../Spinner";
import { cx, type UiSize } from "../utils";
import "./IconButton.css";

type IconButtonVariant = "ghost" | "secondary" | "danger";

type IconButtonProps = {
  "aria-label": string;
  children: ReactNode;
  loading?: boolean;
  size?: UiSize;
  variant?: IconButtonVariant;
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children">;

/** 用途：负责 IconButton 的界面或数据处理职责。 */
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
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <button
      className={cx(
        "ui-icon-button",
        `ui-icon-button--${variant}`,
        `ui-icon-button--${size}`,
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
