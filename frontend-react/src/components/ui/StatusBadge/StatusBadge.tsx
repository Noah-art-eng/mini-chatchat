import type { HTMLAttributes } from "react";
import { cx } from "../utils";
import "./StatusBadge.css";

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

/** 用途：负责 StatusBadge 的界面或数据处理职责。 */
export function StatusBadge({
  className,
  label,
  showDot = true,
  size = "sm",
  status = "neutral",
  ...props
}: StatusBadgeProps) {
  const badgeLabel = label || defaultLabels[status];

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <span
      className={cx(
        "ui-status-badge",
        `ui-status-badge--${status}`,
        `ui-status-badge--${size}`,
        className
      )}
      {...props}
    >
      {showDot && <span className="ui-status-badge__dot" aria-hidden="true" />}
      {badgeLabel}
    </span>
  );
}
