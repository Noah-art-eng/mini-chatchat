import type { HTMLAttributes } from "react";
import { cx } from "../utils";
import "./Spinner.css";

type SpinnerSize = "sm" | "md" | "lg";

type SpinnerProps = {
  ariaLabel?: string;
  decorative?: boolean;
  size?: SpinnerSize;
} & HTMLAttributes<HTMLSpanElement>;

/** 用途：负责 Spinner 的界面或数据处理职责。 */
export function Spinner({
  ariaLabel = "Loading",
  className,
  decorative = false,
  size = "md",
  ...props
}: SpinnerProps) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <span
      aria-hidden={decorative ? true : undefined}
      aria-label={decorative ? undefined : ariaLabel}
      className={cx("ui-spinner", `ui-spinner--${size}`, className)}
      role={decorative ? undefined : "status"}
      {...props}
    />
  );
}
