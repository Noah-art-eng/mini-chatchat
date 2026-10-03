import type { HTMLAttributes, ReactNode } from "react";
import { cx } from "../utils";

type VisuallyHiddenProps = {
  children: ReactNode;
} & HTMLAttributes<HTMLSpanElement>;

export function VisuallyHidden({
  children,
  className,
  ...props
}: VisuallyHiddenProps) {
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
