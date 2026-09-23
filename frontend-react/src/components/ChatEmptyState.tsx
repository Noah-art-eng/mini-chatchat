import {
  BookOpen,
  Bot,
  FilePlus,
  Globe2
} from "lucide-react";
import type { ChatMode } from "../types/chat";
import { useI18n } from "../i18n";
import { BrandLogo } from "./brand";
import { Icon } from "./ui";

type ChatEmptyStateProps = {
  mode: ChatMode;
  onStartMode: (mode: ChatMode) => void;
  onUseSuggestion: (value: string) => void;
};

const actionModes: ChatMode[] = ["local_kb", "search_engine", "temp_kb", "agent"];

const actionIcons = {
  agent: Bot,
  local_kb: BookOpen,
  search_engine: Globe2,
  temp_kb: FilePlus
} satisfies Record<ChatMode, typeof Bot>;

const actionTones = {
  agent: "mcp",
  local_kb: "knowledge",
  search_engine: "browser",
  temp_kb: "file"
} as const;

const actionCopyKeys = {
  agent: "Agent",
  local_kb: "Knowledge",
  search_engine: "Search",
  temp_kb: "Temp"
} as const;

/** 用途：负责 ChatEmptyState 的界面或数据处理职责。 */
export function ChatEmptyState({
  mode,
  onStartMode,
  onUseSuggestion
}: ChatEmptyStateProps) {
  const { t } = useI18n();
  const agentExamples = [
    /** 用途：负责 t 的界面或数据处理职责。 */
    t("onboarding.agentExampleTime"),
    /** 用途：负责 t 的界面或数据处理职责。 */
    t("onboarding.agentExampleNews"),
    /** 用途：负责 t 的界面或数据处理职责。 */
    t("onboarding.agentExampleReadme"),
    /** 用途：负责 t 的界面或数据处理职责。 */
    t("onboarding.agentExampleKnowledge")
  ];

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <section className="chat-empty-state" data-testid="chat-empty-state">
      <div className="empty-brand-mark" aria-hidden="true">
        <BrandLogo size={56} title="" />
      </div>
      <p className="eyebrow">{t(`modes.${mode}`)}</p>
      <h1>{t("onboarding.emptyStartTitle")}</h1>
      <p>{t("onboarding.emptyStartDescription")}</p>
      <div className="empty-action-grid" aria-label={t("chat.availableCapabilities")}>
        {actionModes.map(actionMode => (
          <button
            className={mode === actionMode ? "active" : ""}
            data-testid={`empty-action-${actionMode.replace("_", "-")}`}
            key={actionMode}
            onClick={() => onStartMode(actionMode)}
            type="button"
          >
            <Icon
              icon={actionIcons[actionMode]}
              size="md"
              tone={actionTones[actionMode]}
            />
            <strong>{t(`onboarding.action${actionCopyKeys[actionMode]}Title`)}</strong>
            <span>{t(`onboarding.action${actionCopyKeys[actionMode]}Description`)}</span>
          </button>
        ))}
      </div>
      {mode === "agent" && (
        <div className="suggestion-grid agent-example-grid" aria-label={t("onboarding.agentExamplesTitle")}>
          {agentExamples.map(suggestion => (
            <button
              key={suggestion}
              onClick={() => onUseSuggestion(suggestion)}
              type="button"
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}
      {mode !== "agent" && (
        <div className="suggestion-grid" aria-label={t("chat.suggestionsTitle")}>
          <button
            onClick={() => onUseSuggestion(t("chat.localSuggestion"))}
            type="button"
          >
            {t("chat.localSuggestion")}
          </button>
          <button
            onClick={() => onUseSuggestion(t("chat.searchSuggestion"))}
            type="button"
          >
            {t("chat.searchSuggestion")}
          </button>
        </div>
      )}
    </section>
  );
}
