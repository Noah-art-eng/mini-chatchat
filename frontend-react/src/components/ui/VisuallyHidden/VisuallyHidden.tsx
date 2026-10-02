import type { HTMLAttributes, ReactNode } from "react";
import { cx } from "../utils";

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
    <span
      className={cx(
        "absolute -m-px h-px w-px overflow-hidden border-0 p-0 whitespace-nowrap [clip:rect(0,0,0,0)]",
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
