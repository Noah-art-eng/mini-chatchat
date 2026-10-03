import type { ReactNode } from "react";
import { Button } from "../Button";
import { Stack } from "../Stack";
import { Text } from "../Text";
import { cx } from "../utils";

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

const toneClasses: Record<InlineErrorTone, string> = {
  danger: "border-mc-danger-soft bg-mc-danger-soft",
  warning: "border-mc-warning-soft bg-mc-warning-soft",
};

export function InlineError({
  actionLabel,
  className,
  description,
  message,
  onAction,
  tone = "danger",
  urgent = false
}: InlineErrorProps) {
  return (
    <div
      aria-live={urgent ? undefined : "polite"}
      className={cx(
        "rounded-mc-md border border-solid px-mc-4 py-mc-3",
        toneClasses[tone],
        className
      )}
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
