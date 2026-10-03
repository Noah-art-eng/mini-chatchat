import type { HTMLAttributes } from "react";
import { cx } from "../utils";

type SpinnerSize = "sm" | "md" | "lg";

type SpinnerProps = {
  ariaLabel?: string;
  decorative?: boolean;
  size?: SpinnerSize;
} & HTMLAttributes<HTMLSpanElement>;

const sizeClasses: Record<SpinnerSize, string> = {
  sm: "h-[var(--icon-size-sm)] w-[var(--icon-size-sm)]",
  md: "h-[var(--icon-size-md)] w-[var(--icon-size-md)]",
  lg: "h-[var(--icon-size-lg)] w-[var(--icon-size-lg)]",
};

export function Spinner({
  ariaLabel = "Loading",
  className,
  decorative = false,
  size = "md",
  ...props
}: SpinnerProps) {
  return (
    <span
      aria-hidden={decorative ? true : undefined}
      aria-label={decorative ? undefined : ariaLabel}
      className={cx(
        "inline-flex flex-none animate-[mc-spinner-rotate_var(--motion-duration-slow)_linear_infinite] rounded-mc-circle border-2 border-solid border-mc-border border-t-mc-brand motion-reduce:animate-none",
        sizeClasses[size],
        className
      )}
      role={decorative ? undefined : "status"}
      {...props}
    />
  );
}
