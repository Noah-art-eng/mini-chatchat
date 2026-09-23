import { ToolList } from "./ToolList";
import { useI18n } from "../../i18n";
import type { ToolSpecResponse } from "../../api/system";

type ToolRegistrySectionProps = {
  mcpTools?: ToolSpecResponse[];
  tools: ToolSpecResponse[];
  toolsError: string | null;
};

/** 用途：负责 ToolRegistrySection 的界面或数据处理职责。 */
export function ToolRegistrySection({
  mcpTools = [],
  tools,
  toolsError
}: ToolRegistrySectionProps) {
  const { t } = useI18n();
  const totalTools = tools.length + mcpTools.length;

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article className="settings-card system-wide-card tool-catalog">
      <div className="tool-catalog-header">
        <div>
          <span className="settings-badge status-ok">{totalTools}</span>
          <h2>{t("tools.title")}</h2>
          <p>{t("tools.subtitle")}</p>
        </div>
      </div>
      {toolsError && <p className="inline-error">{toolsError}</p>}
      <ToolList mcpTools={mcpTools} tools={tools} />
    </article>
  );
}
