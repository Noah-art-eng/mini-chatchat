import type { HTMLAttributes } from "react";
import { cx } from "../utils";

type DividerOrientation = "horizontal" | "vertical";
type DividerTone = "subtle" | "default" | "strong";

const orientationClasses: Record<DividerOrientation, string> = {
  horizontal: "w-full border-t border-solid",
  vertical: "min-h-[var(--control-height-sm)] self-stretch border-l border-solid",
};

const toneClasses: Record<DividerTone, string> = {
  subtle: "border-mc-border-subtle",
  default: "border-mc-border",
  strong: "border-mc-border-strong",
};

type DividerProps = {
  orientation?: DividerOrientation;
  tone?: DividerTone;
} & HTMLAttributes<HTMLHRElement>;

export function Divider({
  className,
  orientation = "horizontal",
  tone = "subtle",
  ...props
}: DividerProps) {
  return (
    <hr
      aria-orientation={orientation}
      className={cx(
        "m-0 flex-none border-0",
        orientationClasses[orientation],
        toneClasses[tone],
        className
      )}
      {...props}
    />
  );
}
