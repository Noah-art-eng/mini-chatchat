import type { HTMLAttributes } from "react";
import { cx } from "../utils";

export type StatusBadgeStatus =
  | "neutral"
  | "info"
  | "success"
  | "warning"
  | "danger"
  | "running"
  | "pending"
  | "completed"
  | "failed"
  | "unavailable"
  | "ok"
  | "healthy"
  | "indexed"
  | "uploaded"
  | "degraded"
  | "error";

type StatusBadgeProps = {
  label?: string;
  showDot?: boolean;
  size?: "sm" | "md";
  status?: StatusBadgeStatus;
} & HTMLAttributes<HTMLSpanElement>;

const defaultLabels: Record<StatusBadgeStatus, string> = {
  completed: "Completed",
  danger: "Danger",
  degraded: "Degraded",
  error: "Error",
  failed: "Failed",
  healthy: "Healthy",
  indexed: "Indexed",
  info: "Info",
  neutral: "Neutral",
  ok: "OK",
  pending: "Pending",
  running: "Running",
  success: "Success",
  unavailable: "Unavailable",
  uploaded: "Uploaded",
  warning: "Warning"
};

const sizeClasses: Record<NonNullable<StatusBadgeProps["size"]>, string> = {
  sm: "min-h-[22px] px-mc-2",
  md: "min-h-[26px] px-mc-3",
};

const statusClasses: Record<StatusBadgeStatus, string> = {
  neutral: "bg-mc-subtle text-mc-muted",
  unavailable: "bg-mc-subtle text-mc-muted",
  info: "bg-mc-info-soft text-mc-info",
  running: "bg-mc-info-soft text-mc-info",
  success: "bg-mc-success-soft text-mc-success",
  completed: "bg-mc-success-soft text-mc-success",
  healthy: "bg-mc-success-soft text-mc-success",
  indexed: "bg-mc-success-soft text-mc-success",
  ok: "bg-mc-success-soft text-mc-success",
  warning: "bg-mc-warning-soft text-mc-warning",
  pending: "bg-mc-warning-soft text-mc-warning",
  uploaded: "bg-mc-warning-soft text-mc-warning",
  degraded: "bg-mc-warning-soft text-mc-warning",
  danger: "bg-mc-danger-soft text-mc-danger",
  failed: "bg-mc-danger-soft text-mc-danger",
  error: "bg-mc-danger-soft text-mc-danger",
};

export function StatusBadge({
  className,
  label,
  showDot = true,
  size = "sm",
  status = "neutral",
  ...props
}: StatusBadgeProps) {
  const badgeLabel = label || defaultLabels[status];

  return (
    <span
      className={cx(
        "inline-flex max-w-full items-center gap-mc-1 rounded-mc-pill font-mc-sans text-mc-badge font-mc-semibold",
        statusClasses[status],
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {showDot && (
        <span className="h-[6px] w-[6px] rounded-mc-circle bg-current" aria-hidden="true" />
      )}
      {badgeLabel}
    </span>
  );
}
