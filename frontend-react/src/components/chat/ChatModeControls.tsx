import { Bot, BookOpen, FileText, Globe2 } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { ChatMode } from "../../types/chat";

type ChatModeControlsProps = {
  chatMode: ChatMode;
  kbName: string;
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

/** 用途：负责 ChatModeControls 的界面或数据处理职责。 */
export function ChatModeControls({
  chatMode,
  kbName,
  modes,
  onChangeKbName,
  onChangeMode,
  onOpenModeGuide
}: ChatModeControlsProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="chat-control-bar" aria-label={t("app.currentMode")}>
      <div className="chat-header-actions">
        <div className="mode-toggle mode-cards">
          {modes.map(mode => (
            <button
              className={chatMode === mode ? "active" : ""}
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
        <label className="compact-field">
          <span>{t("app.currentKb")}</span>
          <input
            aria-label={t("app.currentKb")}
            disabled={chatMode !== "local_kb" && chatMode !== "agent"}
            name="current-kb"
            onChange={event => onChangeKbName(event.target.value || "default")}
            value={kbName}
          />
        </label>
        <button
          className="mode-guide-button"
          onClick={onOpenModeGuide}
          type="button"
        >
          {t("onboarding.modeGuideButton")}
        </button>
      </div>
    </div>
  );
}
