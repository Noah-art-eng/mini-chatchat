import { useI18n } from "../i18n";
import { ConfirmDialog as UiConfirmDialog } from "./ui";

type ConfirmDialogProps = {
  cancelLabel?: string;
  confirmLabel?: string;
  description: string;
  isLoading?: boolean;
  isOpen: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  title: string;
};

/** 用途：负责 ConfirmDialog 的界面或数据处理职责。 */
export function ConfirmDialog({
  cancelLabel,
  confirmLabel,
  description,
  isLoading = false,
  isOpen,
  onCancel,
  onConfirm,
  title
}: ConfirmDialogProps) {
  const { t } = useI18n();

  if (!isOpen) return null;

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <UiConfirmDialog
      cancelLabel={cancelLabel || t("common.cancel")}
      confirmLabel={confirmLabel || t("common.confirm")}
      description={description}
      isLoading={isLoading}
      isOpen={isOpen}
      onCancel={onCancel}
      onConfirm={onConfirm}
      title={title}
      variant="danger"
    />
  );
}
