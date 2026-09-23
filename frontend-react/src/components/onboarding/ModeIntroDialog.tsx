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

/** 用途：负责 ModeIntroDialog 的界面或数据处理职责。 */
export function ModeIntroDialog({
  isOpen,
  onClose,
  showDeveloperDetails = false
}: ModeIntroDialogProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <Dialog
      actions={[{ label: t("common.close"), onClick: onClose, variant: "primary" }]}
      className="mode-intro-dialog"
      description={t("onboarding.modeIntroDescription")}
      isOpen={isOpen}
      onClose={onClose}
      size="lg"
      title={t("onboarding.modeIntroTitle")}
    >
      <div className="mode-intro-grid" data-testid="mode-intro-grid">
        {modes.map(item => (
          <article className="mode-intro-card" key={item.key}>
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
