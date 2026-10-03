import { useEffect, useState } from "react";
import {
  getAgentTools,
  getHealth,
  getHealthDeps,
  getMcpServers,
  getMcpTools,
  getModels
} from "../../api/system";
import { SystemWorkspace } from "../../components/system";
import { useI18n } from "../../i18n";
import { useConversationStore } from "../../stores/conversationStore";
import type {
  HealthDepsResponse,
  HealthResponse,
  McpServersResponse,
  McpToolsResponse,
  ToolSpecResponse,
  ModelsResponse
} from "../../api/system";

type SettingsPageProps = {
  onShowModeGuide?: () => void;
  onShowWelcomeGuide?: () => void;
};

export function SettingsPage({
  onShowModeGuide = () => undefined,
  onShowWelcomeGuide = () => undefined
}: SettingsPageProps) {
  const { t } = useI18n();
  const { kbName, chatMode } = useConversationStore();
  const [models, setModels] = useState<ModelsResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [deps, setDeps] = useState<HealthDepsResponse | null>(null);
  const [tools, setTools] = useState<ToolSpecResponse[]>([]);
  const [mcpServers, setMcpServers] = useState<McpServersResponse | null>(null);
  const [mcpTools, setMcpTools] = useState<McpToolsResponse | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading"
  );
  const [error, setError] = useState<string | null>(null);
  const [toolsError, setToolsError] = useState<string | null>(null);
  const [mcpError, setMcpError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    async function loadSystemStatus() {
      setStatus("loading");
      setError(null);
      try {
        const [modelData, healthData, depsData] = await Promise.all([
          getModels(),
          getHealth(),
          getHealthDeps()
        ]);

        if (ignore) return;

        setModels(modelData);
        setHealth(healthData);
        setDeps(depsData);
        setStatus("ready");

        const [toolsResult, mcpServersResult, mcpToolsResult] =
          await Promise.allSettled([
            getAgentTools(),
            getMcpServers(),
            getMcpTools()
          ]);

        if (ignore) return;

        if (toolsResult.status === "fulfilled") {
          setTools(toolsResult.value.tools);
          setToolsError(null);
        } else {
          setTools([]);
          setToolsError(
            toolsResult.reason instanceof Error
              ? toolsResult.reason.message
              : t("settings.toolsLoadFailed")
          );
        }

        let nextMcpError: string | null = null;

        if (mcpServersResult.status === "fulfilled") {
          setMcpServers(mcpServersResult.value);
        } else {
          setMcpServers(null);
          nextMcpError =
            mcpServersResult.reason instanceof Error
              ? mcpServersResult.reason.message
              : t("settings.mcpLoadFailed");
        }

        if (mcpToolsResult.status === "fulfilled") {
          setMcpTools(mcpToolsResult.value);
        } else {
          setMcpTools(null);
          nextMcpError =
            mcpToolsResult.reason instanceof Error
              ? mcpToolsResult.reason.message
              : t("settings.mcpLoadFailed");
        }

        setMcpError(nextMcpError);
      } catch (systemError) {
        if (ignore) return;
        setStatus("error");
        setError(
          systemError instanceof Error
            ? systemError.message
            : t("settings.systemLoadFailed")
        );
      }
    }

    loadSystemStatus().catch(() => undefined);

    return () => {
      ignore = true;
    };
  }, [t]);

  return (
    <SystemWorkspace
      chatMode={chatMode}
      deps={deps}
      error={error}
      health={health}
      kbName={kbName}
      mcpError={mcpError}
      mcpServers={mcpServers}
      mcpTools={mcpTools}
      models={models}
      status={status}
      tools={tools}
      toolsError={toolsError}
      onShowModeGuide={onShowModeGuide}
      onShowWelcomeGuide={onShowWelcomeGuide}
    />
  );
}
