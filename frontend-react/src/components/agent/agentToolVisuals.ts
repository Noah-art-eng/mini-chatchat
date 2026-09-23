import { Wrench } from "lucide-react";
import {
  getToolVisual,
  normalizeToolVisualName,
  type ToolVisualTone
} from "../system/toolVisuals";
import type { LucideIcon } from "lucide-react";
import type { ToolSpecResponse } from "../../api/system";

export type AgentToolVisual = {
  icon: LucideIcon;
  tone: ToolVisualTone;
};

/** 用途：负责 getToolVisualByName 的界面或数据处理职责。 */
export function getToolVisualByName(toolName: string): AgentToolVisual {
  const spec = {
    name: normalizeToolVisualName(toolName),
    tool_name: toolName
  } as ToolSpecResponse;
  const visual = getToolVisual(spec);

  return {
    icon: visual.icon || Wrench,
    tone: visual.tone || "system"
  };
}
