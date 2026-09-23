import type { ToolSpecResponse } from "../../api/system";
import {
  getToolVisual,
  inferToolVisualCategory,
  normalizeToolVisualName,
  type ToolVisualTone
} from "./toolVisuals";
import type { LucideIcon } from "lucide-react";

export type ToolCategory =
  | "all"
  | "recommended"
  | "knowledge"
  | "files"
  | "network"
  | "database"
  | "mcp"
  | "system";

export type ToolCatalogItem = {
  capability: string;
  category: Exclude<ToolCategory, "all" | "recommended">;
  displayName: string;
  fullDescription: string;
  icon: LucideIcon;
  iconTone: ToolVisualTone;
  id: string;
  isMcp: boolean;
  example: string;
  providerLabel: string;
  searchText: string;
  shortDescription: string;
  spec: ToolSpecResponse;
};

const capabilityMap: Record<ToolCatalogItem["category"], string> = {
  database: "Database",
  files: "Files",
  knowledge: "Knowledge",
  mcp: "MCP",
  network: "Web",
  system: "Utility"
};

const recommendedIds = new Set([
  "kb_search",
  "browser_search",
  "filesystem_readonly_read",
  "sqlite_readonly_query",
  "calculator",
  "current_time"
]);

/** 用途：负责 getToolId 的界面或数据处理职责。 */
function getToolId(tool: ToolSpecResponse) {
  return tool.qualified_name || tool.name;
}

/** 用途：负责 normalizeToolName 的界面或数据处理职责。 */
function normalizeToolName(tool: ToolSpecResponse) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (tool.tool_name || tool.name || tool.qualified_name || "").toLowerCase();
}

/** 用途：负责 humanizeToolName 的界面或数据处理职责。 */
function humanizeToolName(name: string) {
  return name
    .split(".")
    .pop()
    ?.replace(/^mcp_/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, char => char.toUpperCase()) || name;
}

/** 用途：负责 getToolCategory 的界面或数据处理职责。 */
function getToolCategory(tool: ToolSpecResponse): ToolCatalogItem["category"] {
  return inferToolVisualCategory(tool);
}

/** 用途：负责 translateMappedValue 的界面或数据处理职责。 */
function translateMappedValue(
  key: string | undefined,
  translate?: (key: string) => string
) {
  if (!key || !translate) return null;
  const value = translate(key);
  return value === key ? null : value;
}

/** 用途：负责 getExampleKey 的界面或数据处理职责。 */
function getExampleKey(name: string) {
  if (name === "browser_search") return "toolExamples.browserSearch";
  if (name === "browser_read") return "toolExamples.browserRead";
  if (name === "calculator") return "toolExamples.calculator";
  if (name === "current_time") return "toolExamples.currentTime";
  if (name === "filesystem_readonly_read" || name === "read_file") {
    return "toolExamples.readFile";
  }
  if (name === "kb_search") return "toolExamples.knowledgeSearch";
  if (name === "sqlite_readonly_query") return "toolExamples.sqliteQuery";
  if (name.includes("directory")) return "toolExamples.directory";
  if (name.includes("server")) return "toolExamples.serverInfo";
  return "toolExamples.generic";
}

/** 用途：负责 toToolCatalogItem 的界面或数据处理职责。 */
export function toToolCatalogItem(
  tool: ToolSpecResponse,
  translate?: (key: string) => string
): ToolCatalogItem {
  const id = getToolId(tool);
  const name = normalizeToolVisualName(tool);
  const category = getToolCategory(tool);
  const visual = getToolVisual(tool);
  const displayName =
    /** 用途：负责 translateMappedValue 的界面或数据处理职责。 */
    translateMappedValue(visual.displayNameKey, translate) ||
    /** 用途：负责 humanizeToolName 的界面或数据处理职责。 */
    humanizeToolName(name || id);
  const shortDescription =
    /** 用途：负责 translateMappedValue 的界面或数据处理职责。 */
    translateMappedValue(visual.descriptionKey, translate) ||
    tool.description ||
    "Use this tool as part of an agent workflow.";
  const fullDescription = tool.description || shortDescription;
  const example =
    /** 用途：负责 translateMappedValue 的界面或数据处理职责。 */
    translateMappedValue(getExampleKey(name), translate) ||
    "Ask the agent to use this capability when it is relevant.";
  const providerLabel =
    category === "mcp"
      ? tool.server_name || "MCP"
      : tool.provider || "Local";

  return {
    capability: capabilityMap[category],
    category,
    displayName,
    fullDescription,
    icon: visual.icon,
    iconTone: visual.tone,
    id,
    isMcp: category === "mcp",
    example,
    providerLabel,
    searchText: [
      id,
      name,
      displayName,
      shortDescription,
      fullDescription,
      example,
      category,
      providerLabel
    ]
      .join(" ")
      .toLowerCase(),
    shortDescription,
    spec: tool
  };
}

/** 用途：负责 isRecommendedTool 的界面或数据处理职责。 */
export function isRecommendedTool(tool: ToolCatalogItem) {
  return recommendedIds.has(normalizeToolName(tool.spec));
}

export const toolCategoryOrder: Exclude<ToolCategory, "all" | "recommended">[] = [
  "knowledge",
  "files",
  "network",
  "database",
  "mcp",
  "system"
];
