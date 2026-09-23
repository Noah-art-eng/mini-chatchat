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

/** 用途：负责 WelcomeDialog 的界面或数据处理职责。 */
export function WelcomeDialog({ isOpen, onComplete }: WelcomeDialogProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
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
      className="onboarding-dialog"
      description={t("onboarding.welcomeDescription")}
      isOpen={isOpen}
      onClose={onComplete}
      size="lg"
      title={t("onboarding.welcomeTitle")}
    >
      <div className="onboarding-brand">
        <BrandLogo size={56} title={t("app.name")} />
      </div>
      <div className="onboarding-capability-grid">
        {capabilities.map(item => (
          <article className="onboarding-capability-card" key={item.key}>
            <Icon icon={item.icon} size="md" tone={item.tone} />
            <strong>{t(`onboarding.${item.key}Title`)}</strong>
            <p>{t(`onboarding.${item.key}Description`)}</p>
          </article>
        ))}
      </div>
    </Dialog>
  );
}
