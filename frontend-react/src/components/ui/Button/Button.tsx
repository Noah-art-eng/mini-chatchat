import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Spinner } from "../Spinner";
import { cx, type UiSize } from "../utils";
import "./Button.css";

type ButtonVariant = "primary" | "secondary" | "ghost" | "outline" | "danger" | "quiet";

type ButtonProps = {
  leadingIcon?: ReactNode;
  loading?: boolean;
  size?: UiSize;
  trailingIcon?: ReactNode;
  variant?: ButtonVariant;
} & ButtonHTMLAttributes<HTMLButtonElement>;

/** 用途：负责 Button 的界面或数据处理职责。 */
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

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <button
      className={cx(
        "ui-button",
        `ui-button--${variant}`,
        `ui-button--${size}`,
        loading && "ui-button--loading",
        className
      )}
      disabled={isDisabled}
      type={type}
      {...props}
    >
      {loading && <Spinner ariaLabel="Loading" size="sm" />}
      {!loading && leadingIcon && (
        <span className="ui-button__icon" aria-hidden="true">
          {leadingIcon}
        </span>
      )}
      <span className="ui-button__label">{children}</span>
      {!loading && trailingIcon && (
        <span className="ui-button__icon" aria-hidden="true">
          {trailingIcon}
        </span>
      )}
    </button>
  );
}
