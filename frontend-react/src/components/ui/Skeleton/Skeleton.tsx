import type { HTMLAttributes } from "react";
import { cx } from "../utils";

type SkeletonVariant = "text" | "row" | "card" | "table";
type SkeletonSize = "sm" | "md" | "lg";

type SkeletonProps = {
  count?: number;
  size?: SkeletonSize;
  variant?: SkeletonVariant;
} & HTMLAttributes<HTMLDivElement>;

const sizeClasses: Record<SkeletonSize, string> = {
  sm: "h-[10px]",
  md: "h-[14px]",
  lg: "h-[18px]",
};

const variantClasses: Record<SkeletonVariant, string> = {
  text: "",
  row: "min-h-[var(--list-row-height)]",
  card: "min-h-[112px] rounded-mc-lg",
  table: "min-h-[var(--table-row-height)]",
};

export function Skeleton({
  className,
  count = 1,
  size = "md",
  variant = "text",
  ...props
}: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cx("grid gap-mc-2", className)}
      {...props}
    >
      {Array.from({ length: count }).map((_, index) => (
        <span
          className={cx(
            "block w-full min-w-0 animate-[mc-skeleton-shimmer_1.35s_var(--motion-ease-standard)_infinite] rounded-mc-md bg-[linear-gradient(90deg,var(--color-bg-subtle),var(--color-bg-hover),var(--color-bg-subtle))] bg-[length:220%_100%] motion-reduce:animate-none motion-reduce:bg-mc-subtle",
            variantClasses[variant],
            variant === "text" && sizeClasses[size]
          )}
          key={index}
        />
      ))}
    </div>
  );
}
