import type { HTMLAttributes } from "react";
import { cx } from "../utils";
import "./Skeleton.css";

type SkeletonVariant = "text" | "row" | "card" | "table";
type SkeletonSize = "sm" | "md" | "lg";

type SkeletonProps = {
  count?: number;
  size?: SkeletonSize;
  variant?: SkeletonVariant;
} & HTMLAttributes<HTMLDivElement>;

/** 用途：负责 Skeleton 的界面或数据处理职责。 */
export function Skeleton({
  className,
  count = 1,
  size = "md",
  variant = "text",
  ...props
}: SkeletonProps) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div
      aria-hidden="true"
      className={cx("ui-skeleton-group", className)}
      {...props}
    >
      {Array.from({ length: count }).map((_, index) => (
        <span
          className={cx(
            "ui-skeleton",
            `ui-skeleton--${variant}`,
            `ui-skeleton--${size}`
          )}
          key={index}
        />
      ))}
    </div>
  );
}
