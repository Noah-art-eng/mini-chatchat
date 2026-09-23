import type { ReactNode } from "react";
import { Dialog } from "./Dialog";

type ConfirmDialogProps = {
  body?: ReactNode;
  cancelLabel?: string;
  confirmLabel?: string;
  description: ReactNode;
  error?: string | null;
  isLoading?: boolean;
  isOpen: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  title: ReactNode;
  variant?: "confirm" | "danger";
};

/** 用途：负责 ConfirmDialog 的界面或数据处理职责。 */
export function ConfirmDialog({
  body,
  cancelLabel = "Cancel",
  confirmLabel = "Confirm",
  description,
  error,
  isLoading = false,
  isOpen,
  onCancel,
  onConfirm,
  title,
  variant = "danger"
}: ConfirmDialogProps) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <Dialog
      actions={[
        {
          disabled: isLoading,
          label: cancelLabel,
          onClick: onCancel,
          variant: "secondary"
        },
        {
          label: confirmLabel,
          loading: isLoading,
          onClick: onConfirm,
          variant: variant === "danger" ? "danger" : "primary"
        }
      ]}
      description={description}
      error={error}
      initialFocus="cancel"
      isOpen={isOpen}
      onClose={onCancel}
      preventClose={isLoading}
      size="sm"
      title={title}
    >
      {body}
    </Dialog>
  );
}
