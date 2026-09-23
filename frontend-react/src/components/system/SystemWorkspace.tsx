import { DependencySection } from "./DependencySection";
import { EmptySystemState } from "./EmptySystemState";
import { HealthOverview } from "./HealthOverview";
import { MCPSection } from "./MCPSection";
import { ModelSection } from "./ModelSection";
import { RuntimeInfo } from "./RuntimeInfo";
import { SystemHeader } from "./SystemHeader";
import { ToolRegistrySection } from "./ToolRegistrySection";
import { useI18n } from "../../i18n";
import { Button } from "../ui";
import type {
  HealthDepsResponse,
  HealthResponse,
  McpServersResponse,
  McpToolsResponse,
  ModelsResponse,
  ToolSpecResponse
} from "../../api/system";
import type { ChatMode } from "../../types/chat";

type SystemWorkspaceProps = {
  chatMode: ChatMode;
  deps: HealthDepsResponse | null;
  error: string | null;
  health: HealthResponse | null;
  kbName: string;
  mcpError: string | null;
  mcpServers: McpServersResponse | null;
  mcpTools: McpToolsResponse | null;
  models: ModelsResponse | null;
  onShowModeGuide: () => void;
  onShowWelcomeGuide: () => void;
  status: "loading" | "ready" | "error";
  tools: ToolSpecResponse[];
  toolsError: string | null;
};

/** 用途：负责 SystemWorkspace 的界面或数据处理职责。 */
export function SystemWorkspace({
  chatMode,
  deps,
  error,
  health,
  kbName,
  mcpError,
  mcpServers,
  mcpTools,
  models,
  onShowModeGuide,
  onShowWelcomeGuide,
  status,
  tools,
  toolsError
}: SystemWorkspaceProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <section className="page-surface system-page" aria-label={t("settings.title")}>
      <SystemHeader health={health} status={status} />
      {status === "loading" && <EmptySystemState />}
      {status === "error" && (
        <p className="inline-error">{error || t("settings.systemLoadFailed")}</p>
      )}

      <div className="settings-grid system-workspace-grid">
        <HealthOverview health={health} status={status} />
        <ModelSection chatMode={chatMode} kbName={kbName} models={models} />
        <section className="settings-card guide-settings-card">
          <div className="settings-card-heading">
            <p className="eyebrow">{t("settings.guides")}</p>
            <h2>{t("settings.guidesTitle")}</h2>
            <p>{t("settings.guidesDescription")}</p>
          </div>
          <div className="guide-settings-actions">
            <Button onClick={onShowWelcomeGuide} variant="secondary">
              {t("settings.showWelcomeGuide")}
            </Button>
            <Button onClick={onShowModeGuide} variant="quiet">
              {t("settings.showModeGuide")}
            </Button>
          </div>
        </section>
        <DependencySection deps={deps} status={status} />
        <ToolRegistrySection
          mcpTools={mcpTools?.tools || []}
          tools={tools}
          toolsError={toolsError}
        />
        <MCPSection
          mcpError={mcpError}
          mcpServers={mcpServers}
          mcpTools={mcpTools}
        />
        <RuntimeInfo health={health} models={models} />
      </div>
    </section>
  );
}
