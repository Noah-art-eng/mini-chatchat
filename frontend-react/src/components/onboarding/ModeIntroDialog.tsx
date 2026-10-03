import { Bot, BookOpen, FilePlus, Globe2 } from "lucide-react";
import { useI18n } from "../../i18n";
import { Dialog, Icon } from "../ui";

type ModeIntroDialogProps = {
  isOpen: boolean;
  onClose: () => void;
  showDeveloperDetails?: boolean;
};

const modes = [
  { icon: BookOpen, key: "local", tone: "knowledge" },
  { icon: Globe2, key: "search", tone: "browser" },
  { icon: FilePlus, key: "temp", tone: "file" },
  { icon: Bot, key: "agent", tone: "mcp" }
] as const;

export function ModeIntroDialog({
  isOpen,
  onClose,
  showDeveloperDetails = false
}: ModeIntroDialogProps) {
  const { t } = useI18n();

  return (
    <Dialog
      actions={[{ label: t("common.close"), onClick: onClose, variant: "primary" }]}
      className="mode-intro-dialog [&_.ui-dialog__header]:text-center"
      description={t("onboarding.modeIntroDescription")}
      isOpen={isOpen}
      onClose={onClose}
      size="lg"
      title={t("onboarding.modeIntroTitle")}
    >
      <div className="grid grid-cols-2 gap-mc-3 max-[640px]:grid-cols-1" data-testid="mode-intro-grid">
        {modes.map(item => (
          <article className="grid grid-cols-[auto_1fr] gap-mc-2 rounded-mc-lg border border-mc-border-subtle bg-[color-mix(in_srgb,var(--color-bg-surface)_82%,transparent)] p-mc-4 [&_p]:m-[0] [&_p]:text-mc-body-small [&_p]:text-mc-secondary [&_small]:mt-mc-2 [&_small]:block [&_small]:text-mc-muted [&_code]:mt-mc-2 [&_code]:inline-flex [&_code]:w-fit [&_code]:rounded-mc-sm [&_code]:bg-mc-subtle [&_code]:px-mc-2 [&_code]:py-mc-1 [&_code]:text-mc-caption [&_code]:text-mc-muted" key={item.key}>
            <Icon icon={item.icon} size="md" tone={item.tone} />
            <div>
              <strong>{t(`onboarding.mode${item.key}Title`)}</strong>
              <p>{t(`onboarding.mode${item.key}Description`)}</p>
              <small>{t(`onboarding.mode${item.key}Example`)}</small>
              {showDeveloperDetails && (
                <code>{t(`onboarding.mode${item.key}Id`)}</code>
              )}
            </div>
          </article>
        ))}
      </div>
    </Dialog>
  );
}
