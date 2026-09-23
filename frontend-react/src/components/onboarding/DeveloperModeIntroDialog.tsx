import { Code2 } from "lucide-react";
import { useI18n } from "../../i18n";
import { Dialog, Icon } from "../ui";

type DeveloperModeIntroDialogProps = {
  isOpen: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

/** 用途：负责 DeveloperModeIntroDialog 的界面或数据处理职责。 */
export function DeveloperModeIntroDialog({
  isOpen,
  onCancel,
  onConfirm
}: DeveloperModeIntroDialogProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <Dialog
      actions={[
        {
          label: t("common.cancel"),
          onClick: onCancel,
          variant: "secondary"
        },
        {
          label: t("onboarding.enableDeveloperMode"),
          onClick: onConfirm,
          variant: "primary"
        }
      ]}
      className="developer-mode-intro-dialog"
      description={t("onboarding.developerIntroDescription")}
      isOpen={isOpen}
      onClose={onCancel}
      size="md"
      title={t("onboarding.developerIntroTitle")}
    >
      <div className="developer-intro-body">
        <Icon icon={Code2} size="lg" tone="mcp" />
        <p>{t("onboarding.developerIntroBody")}</p>
      </div>
    </Dialog>
  );
}
