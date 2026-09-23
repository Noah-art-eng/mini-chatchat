import {
  BookOpen,
  Calculator,
  Clock3,
  Database,
  FileCog,
  FileSearch,
  FileText,
  Files,
  FolderLock,
  FolderOpen,
  FolderTree,
  Globe2,
  Info,
  MessageSquare,
  PanelsTopLeft,
  Search,
  Server,
  SquareTerminal,
  Wrench,
  type LucideIcon
} from "lucide-react";
import type { ToolSpecResponse } from "../../api/system";

export type ToolVisualCategory =
  | "knowledge"
  | "files"
  | "network"
  | "database"
  | "mcp"
  | "system";

export type ToolVisualTone =
  | "knowledge"
  | "file"
  | "browser"
  | "database"
  | "mcp"
  | "system";

export type ToolVisual = {
  category: ToolVisualCategory;
  descriptionKey?: string;
  displayNameKey?: string;
  icon: LucideIcon;
  tone: ToolVisualTone;
};

const fallbackVisualByCategory: Record<ToolVisualCategory, ToolVisual> = {
  database: { category: "database", icon: Database, tone: "database" },
  files: { category: "files", icon: FileText, tone: "file" },
  knowledge: { category: "knowledge", icon: BookOpen, tone: "knowledge" },
  mcp: { category: "mcp", icon: Server, tone: "mcp" },
  network: { category: "network", icon: Globe2, tone: "browser" },
  system: { category: "system", icon: Wrench, tone: "system" }
};

const visualMap: Record<string, ToolVisual> = {
  browser_read: {
    category: "network",
    descriptionKey: "toolDescriptions.browserRead",
    displayNameKey: "toolNames.browserRead",
    icon: PanelsTopLeft,
    tone: "browser"
  },
  browser_search: {
    category: "network",
    descriptionKey: "toolDescriptions.browserSearch",
    displayNameKey: "toolNames.browserSearch",
    icon: Search,
    tone: "browser"
  },
  calculator: {
    category: "system",
    descriptionKey: "toolDescriptions.calculator",
    displayNameKey: "toolNames.calculator",
    icon: Calculator,
    tone: "system"
  },
  current_time: {
    category: "system",
    descriptionKey: "toolDescriptions.currentTime",
    displayNameKey: "toolNames.currentTime",
    icon: Clock3,
    tone: "system"
  },
  directory_tree: {
    category: "files",
    descriptionKey: "toolDescriptions.directoryTree",
    displayNameKey: "toolNames.directoryTree",
    icon: FolderTree,
    tone: "file"
  },
  filesystem_readonly_read: {
    category: "files",
    descriptionKey: "toolDescriptions.readFile",
    displayNameKey: "toolNames.readFile",
    icon: FileText,
    tone: "file"
  },
  get_file_info: {
    category: "files",
    descriptionKey: "toolDescriptions.getFileInfo",
    displayNameKey: "toolNames.getFileInfo",
    icon: FileCog,
    tone: "file"
  },
  kb_search: {
    category: "knowledge",
    descriptionKey: "toolDescriptions.knowledgeSearch",
    displayNameKey: "toolNames.knowledgeSearch",
    icon: BookOpen,
    tone: "knowledge"
  },
  list_allowed_directories: {
    category: "system",
    descriptionKey: "toolDescriptions.allowedDirectories",
    displayNameKey: "toolNames.allowedDirectories",
    icon: FolderLock,
    tone: "system"
  },
  list_directory: {
    category: "files",
    descriptionKey: "toolDescriptions.listDirectory",
    displayNameKey: "toolNames.listDirectory",
    icon: FolderOpen,
    tone: "file"
  },
  mcp_demo_echo: {
    category: "mcp",
    descriptionKey: "toolDescriptions.mcpDemoEcho",
    displayNameKey: "toolNames.mcpDemoEcho",
    icon: MessageSquare,
    tone: "mcp"
  },
  read_file: {
    category: "files",
    descriptionKey: "toolDescriptions.readFile",
    displayNameKey: "toolNames.readFile",
    icon: FileText,
    tone: "file"
  },
  read_multiple_files: {
    category: "files",
    descriptionKey: "toolDescriptions.readMultipleFiles",
    displayNameKey: "toolNames.readMultipleFiles",
    icon: Files,
    tone: "file"
  },
  search_files: {
    category: "files",
    descriptionKey: "toolDescriptions.searchFiles",
    displayNameKey: "toolNames.searchFiles",
    icon: FileSearch,
    tone: "file"
  },
  server_info: {
    category: "mcp",
    descriptionKey: "toolDescriptions.serverInfo",
    displayNameKey: "toolNames.serverInfo",
    icon: Server,
    tone: "mcp"
  },
  sqlite_readonly_query: {
    category: "database",
    descriptionKey: "toolDescriptions.sqliteQuery",
    displayNameKey: "toolNames.sqliteQuery",
    icon: Database,
    tone: "database"
  },
  stderr_read: {
    category: "system",
    descriptionKey: "toolDescriptions.commandOutput",
    displayNameKey: "toolNames.commandOutput",
    icon: SquareTerminal,
    tone: "system"
  },
  stdout_read: {
    category: "system",
    descriptionKey: "toolDescriptions.commandOutput",
    displayNameKey: "toolNames.commandOutput",
    icon: SquareTerminal,
    tone: "system"
  }
};

/** 用途：负责 getToolId 的界面或数据处理职责。 */
function getToolId(tool: ToolSpecResponse) {
  return tool.qualified_name || tool.name;
}

/** 用途：负责 normalizeToolVisualName 的界面或数据处理职责。 */
export function normalizeToolVisualName(tool: ToolSpecResponse | string) {
  const raw =
    typeof tool === "string"
      ? tool
      : tool.tool_name || tool.name || tool.qualified_name || "";

  const normalized = raw
    .toLowerCase()
    .replace(/^mcp\./, "")
    .replace(/[.:-]+/g, "_");

  if (normalized.endsWith("_read_file")) return "read_file";
  if (normalized.endsWith("_read_multiple_files")) return "read_multiple_files";
  if (normalized.endsWith("_list_directory")) return "list_directory";
  if (normalized.endsWith("_directory_tree")) return "directory_tree";
  if (normalized.endsWith("_search_files")) return "search_files";
  if (normalized.endsWith("_get_file_info")) return "get_file_info";
  if (normalized.endsWith("_list_allowed_directories")) {
    return "list_allowed_directories";
  }
  if (normalized.endsWith("_stdout_read")) return "stdout_read";
  if (normalized.endsWith("_stderr_read")) return "stderr_read";
  if (normalized.endsWith("_server_info")) return "server_info";
  if (normalized.endsWith("_echo")) return "mcp_demo_echo";

  return normalized;
}

/** 用途：负责 inferToolVisualCategory 的界面或数据处理职责。 */
export function inferToolVisualCategory(tool: ToolSpecResponse): ToolVisualCategory {
  const id = getToolId(tool).toLowerCase();
  const name = normalizeToolVisualName(tool);
  const provider = (tool.provider || "").toLowerCase();

  if (name.includes("kb") || name.includes("knowledge")) return "knowledge";
  if (name.includes("sqlite") || name.includes("database")) return "database";
  if (name.includes("browser") || name.includes("web")) return "network";
  if (name.includes("file") || name.includes("directory")) return "files";
  if (provider === "mcp" || id.startsWith("mcp.") || tool.server_name) return "mcp";
  if (name.includes("search")) return "network";
  return "system";
}

/** 用途：负责 getToolVisual 的界面或数据处理职责。 */
export function getToolVisual(tool: ToolSpecResponse): ToolVisual {
  const category = inferToolVisualCategory(tool);
  return visualMap[normalizeToolVisualName(tool)] || fallbackVisualByCategory[category];
}

/** 用途：负责 getFallbackToolIcon 的界面或数据处理职责。 */
export function getFallbackToolIcon(category: ToolVisualCategory) {
  return fallbackVisualByCategory[category].icon || Info;
}
