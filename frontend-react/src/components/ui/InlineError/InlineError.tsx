import type { ReactNode } from "react";
import { Button } from "../Button";
import { Stack } from "../Stack";
import { Text } from "../Text";
import { cx } from "../utils";
import "./InlineError.css";

type InlineErrorTone = "danger" | "warning";

type InlineErrorProps = {
  actionLabel?: string;
  className?: string;
  description?: ReactNode;
  message: ReactNode;
  onAction?: () => void;
  urgent?: boolean;
  tone?: InlineErrorTone;
};

/** 用途：负责 InlineError 的界面或数据处理职责。 */
export function InlineError({
  actionLabel,
  className,
  description,
  message,
  onAction,
  tone = "danger",
  urgent = false
}: InlineErrorProps) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div
      aria-live={urgent ? undefined : "polite"}
      className={cx("ui-inline-error", `ui-inline-error--${tone}`, className)}
      role={urgent ? "alert" : "status"}
    >
      <Stack gap="2">
        <Text as="strong" tone={tone} variant="label">
          {message}
        </Text>
        {description && (
          <Text tone={tone} variant="bodySmall">
            {description}
          </Text>
        )}
        {actionLabel && onAction && (
          <div>
            <Button onClick={onAction} size="sm" variant="secondary">
              {actionLabel}
            </Button>
          </div>
        )}
      </Stack>
    </div>
  );
}
