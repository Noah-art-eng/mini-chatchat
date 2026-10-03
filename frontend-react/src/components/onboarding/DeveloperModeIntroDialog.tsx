import { Code2 } from "lucide-react";
import { useI18n } from "../../i18n";
import { Dialog, Icon } from "../ui";

type DeveloperModeIntroDialogProps = {
  isOpen: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export function DeveloperModeIntroDialog({
  isOpen,
  onCancel,
  onConfirm
}: DeveloperModeIntroDialogProps) {
  const { t } = useI18n();

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
      className="developer-mode-intro-dialog [&_.ui-dialog__header]:text-center"
      description={t("onboarding.developerIntroDescription")}
      isOpen={isOpen}
      onClose={onCancel}
      size="md"
      title={t("onboarding.developerIntroTitle")}
    >
      <div className="grid justify-items-center gap-mc-3 text-center [&_p]:m-[0] [&_p]:max-w-[46ch] [&_p]:text-mc-secondary">
        <Icon icon={Code2} size="lg" tone="mcp" />
        <p>{t("onboarding.developerIntroBody")}</p>
      </div>
    </Dialog>
  );
}
