import { Bot, BookOpen, FileText, Globe2 } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { ChatMode } from "../../types/chat";
import { cx } from "../ui/utils";
import { chatStyles } from "./chatStyles";

type ChatModeControlsProps = {
  chatMode: ChatMode;
  kbName: string;
  knowledgeBaseNames: string[];
  modes: ChatMode[];
  onChangeKbName: (kbName: string) => void;
  onChangeMode: (mode: ChatMode) => void;
  onOpenModeGuide: () => void;
};

const modeIcons = {
  agent: Bot,
  local_kb: BookOpen,
  search_engine: Globe2,
  temp_kb: FileText
} satisfies Record<ChatMode, typeof Bot>;

const modeTones = {
  agent: "mcp",
  local_kb: "knowledge",
  search_engine: "browser",
  temp_kb: "file"
} as const;

export function ChatModeControls({
  chatMode,
  kbName,
  knowledgeBaseNames,
  modes,
  onChangeKbName,
  onChangeMode,
  onOpenModeGuide
}: ChatModeControlsProps) {
  const { t } = useI18n();

  return (
    <div className={chatStyles.controls} aria-label={t("app.currentMode")}>
      <div className={chatStyles.controlRow}>
        <div className={chatStyles.modeGrid}>
          {modes.map(mode => (
            <button
              className={cx(chatStyles.modeButton, chatMode === mode && chatStyles.modeButtonActive)}
              data-testid={`chat-mode-${mode.replace("_", "-")}`}
              key={mode}
              onClick={() => onChangeMode(mode)}
              type="button"
            >
              <span>
                <Icon icon={modeIcons[mode]} size="sm" tone={modeTones[mode]} />
                {t(`modes.${mode}`)}
              </span>
              <small>{t(`modeDescriptions.${mode}`)}</small>
            </button>
          ))}
        </div>
        <label className={chatStyles.compactField}>
          <span>{t("app.currentKb")}</span>
          <select
            aria-label={t("app.currentKb")}
            disabled={chatMode !== "local_kb" && chatMode !== "agent"}
            name="current-kb"
            onChange={event => onChangeKbName(event.target.value)}
            value={kbName}
          >
            {knowledgeBaseNames.length === 0 && <option value={kbName}>{kbName}</option>}
            {knowledgeBaseNames.map(name => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </label>
        <button
          className={chatStyles.guideButton}
          onClick={onOpenModeGuide}
          type="button"
        >
          {t("onboarding.modeGuideButton")}
        </button>
      </div>
    </div>
  );
}
