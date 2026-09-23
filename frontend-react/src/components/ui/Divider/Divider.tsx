import type { HTMLAttributes } from "react";
import { cx } from "../utils";
import "./Divider.css";

type DividerOrientation = "horizontal" | "vertical";
type DividerTone = "subtle" | "default" | "strong";

type DividerProps = {
  orientation?: DividerOrientation;
  tone?: DividerTone;
} & HTMLAttributes<HTMLHRElement>;

/** 用途：负责 Divider 的界面或数据处理职责。 */
export function Divider({
  className,
  orientation = "horizontal",
  tone = "subtle",
  ...props
}: DividerProps) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <hr
      aria-orientation={orientation}
      className={cx(
        "ui-divider",
        `ui-divider--${orientation}`,
        `ui-divider--${tone}`,
        className
      )}
      {...props}
    />
  );
}
