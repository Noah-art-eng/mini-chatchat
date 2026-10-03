import { Bot, BookOpen, FilePlus, Globe2 } from "lucide-react";
import { useI18n } from "../../i18n";
import { BrandLogo } from "../brand";
import { Dialog, Icon } from "../ui";

type WelcomeDialogProps = {
  isOpen: boolean;
  onComplete: () => void;
};

const capabilities = [
  { icon: BookOpen, key: "knowledge", tone: "knowledge" },
  { icon: Globe2, key: "search", tone: "browser" },
  { icon: FilePlus, key: "temp", tone: "file" },
  { icon: Bot, key: "agent", tone: "mcp" }
] as const;

export function WelcomeDialog({ isOpen, onComplete }: WelcomeDialogProps) {
  const { t } = useI18n();

  return (
    <Dialog
      actions={[
        {
          label: t("onboarding.skip"),
          onClick: onComplete,
          variant: "secondary"
        },
        {
          label: t("onboarding.getStarted"),
          onClick: onComplete,
          variant: "primary"
        }
      ]}
      className="onboarding-dialog [&_.ui-dialog__header]:text-center"
      description={t("onboarding.welcomeDescription")}
      isOpen={isOpen}
      onClose={onComplete}
      size="lg"
      title={t("onboarding.welcomeTitle")}
    >
      <div className="my-mc-2 mb-mc-5 flex justify-center">
        <BrandLogo size={56} title={t("app.name")} />
      </div>
      <div className="grid grid-cols-2 gap-mc-3 max-[640px]:grid-cols-1">
        {capabilities.map(item => (
          <article className="grid gap-mc-2 rounded-mc-lg border border-mc-border-subtle bg-[color-mix(in_srgb,var(--color-bg-surface)_82%,transparent)] p-mc-4 [&_p]:m-[0] [&_p]:text-mc-body-small [&_p]:text-mc-secondary" key={item.key}>
            <Icon icon={item.icon} size="md" tone={item.tone} />
            <strong>{t(`onboarding.${item.key}Title`)}</strong>
            <p>{t(`onboarding.${item.key}Description`)}</p>
          </article>
        ))}
      </div>
    </Dialog>
  );
}
