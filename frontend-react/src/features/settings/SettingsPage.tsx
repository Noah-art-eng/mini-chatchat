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

/** 用途：负责 SettingsPage 的界面或数据处理职责。 */
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

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    let ignore = false;

    /** 用途：负责 loadSystemStatus 的界面或数据处理职责。 */
    async function loadSystemStatus() {
      /** 用途：负责 setStatus 的界面或数据处理职责。 */
      setStatus("loading");
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(null);
      try {
        const [modelData, healthData, depsData] = await Promise.all([
          /** 用途：负责 getModels 的界面或数据处理职责。 */
          getModels(),
          /** 用途：负责 getHealth 的界面或数据处理职责。 */
          getHealth(),
          /** 用途：负责 getHealthDeps 的界面或数据处理职责。 */
          getHealthDeps()
        ]);

        if (ignore) return;

        /** 用途：负责 setModels 的界面或数据处理职责。 */
        setModels(modelData);
        /** 用途：负责 setHealth 的界面或数据处理职责。 */
        setHealth(healthData);
        /** 用途：负责 setDeps 的界面或数据处理职责。 */
        setDeps(depsData);
        /** 用途：负责 setStatus 的界面或数据处理职责。 */
        setStatus("ready");

        const [toolsResult, mcpServersResult, mcpToolsResult] =
          await Promise.allSettled([
            /** 用途：负责 getAgentTools 的界面或数据处理职责。 */
            getAgentTools(),
            /** 用途：负责 getMcpServers 的界面或数据处理职责。 */
            getMcpServers(),
            /** 用途：负责 getMcpTools 的界面或数据处理职责。 */
            getMcpTools()
          ]);

        if (ignore) return;

        if (toolsResult.status === "fulfilled") {
          /** 用途：负责 setTools 的界面或数据处理职责。 */
          setTools(toolsResult.value.tools);
          /** 用途：负责 setToolsError 的界面或数据处理职责。 */
          setToolsError(null);
        } else {
          /** 用途：负责 setTools 的界面或数据处理职责。 */
          setTools([]);
          /** 用途：负责 setToolsError 的界面或数据处理职责。 */
          setToolsError(
            toolsResult.reason instanceof Error
              ? toolsResult.reason.message
              : t("settings.toolsLoadFailed")
          );
        }

        let nextMcpError: string | null = null;

        if (mcpServersResult.status === "fulfilled") {
          /** 用途：负责 setMcpServers 的界面或数据处理职责。 */
          setMcpServers(mcpServersResult.value);
        } else {
          /** 用途：负责 setMcpServers 的界面或数据处理职责。 */
          setMcpServers(null);
          nextMcpError =
            mcpServersResult.reason instanceof Error
              ? mcpServersResult.reason.message
              : t("settings.mcpLoadFailed");
        }

        if (mcpToolsResult.status === "fulfilled") {
          /** 用途：负责 setMcpTools 的界面或数据处理职责。 */
          setMcpTools(mcpToolsResult.value);
        } else {
          /** 用途：负责 setMcpTools 的界面或数据处理职责。 */
          setMcpTools(null);
          nextMcpError =
            mcpToolsResult.reason instanceof Error
              ? mcpToolsResult.reason.message
              : t("settings.mcpLoadFailed");
        }

        /** 用途：负责 setMcpError 的界面或数据处理职责。 */
        setMcpError(nextMcpError);
      } catch (systemError) {
        if (ignore) return;
        /** 用途：负责 setStatus 的界面或数据处理职责。 */
        setStatus("error");
        /** 用途：负责 setError 的界面或数据处理职责。 */
        setError(
          systemError instanceof Error
            ? systemError.message
            : t("settings.systemLoadFailed")
        );
      }
    }

    /** 用途：负责 loadSystemStatus 的界面或数据处理职责。 */
    loadSystemStatus().catch(() => undefined);

    /** 用途：负责 return 的界面或数据处理职责。 */
    return () => {
      ignore = true;
    };
  }, [t]);

  /** 用途：负责 return 的界面或数据处理职责。 */
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
