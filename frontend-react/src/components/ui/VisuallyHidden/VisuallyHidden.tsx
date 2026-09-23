import type { HTMLAttributes, ReactNode } from "react";
import { cx } from "../utils";
import "./VisuallyHidden.css";

type VisuallyHiddenProps = {
  children: ReactNode;
} & HTMLAttributes<HTMLSpanElement>;

/** 用途：负责 VisuallyHidden 的界面或数据处理职责。 */
export function VisuallyHidden({
  children,
  className,
  ...props
}: VisuallyHiddenProps) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <span className={cx("ui-visually-hidden", className)} {...props}>
      {children}
    </span>
  );
}
