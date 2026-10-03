import { ToolList } from "./ToolList";
import { useI18n } from "../../i18n";
import type { ToolSpecResponse } from "../../api/system";
import { systemBadgeClassName, systemCardClassName } from "./systemStyles";

type ToolRegistrySectionProps = {
  mcpTools?: ToolSpecResponse[];
  tools: ToolSpecResponse[];
  toolsError: string | null;
};

export function ToolRegistrySection({
  mcpTools = [],
  tools,
  toolsError
}: ToolRegistrySectionProps) {
  const { t } = useI18n();
  const totalTools = tools.length + mcpTools.length;

  return (
    <article className={`${systemCardClassName} system-wide-card tool-catalog col-span-full overflow-hidden`}>
      <div className="tool-catalog-header mb-mc-5 flex items-start justify-between gap-mc-4 [&_h2]:m-0 [&_p]:m-0 [&_p]:mt-mc-1 [&_p]:text-mc-body-small [&_p]:text-mc-secondary">
        <div>
          <span className={`${systemBadgeClassName} status-ok`}>{totalTools}</span>
          <h2>{t("tools.title")}</h2>
          <p>{t("tools.subtitle")}</p>
        </div>
      </div>
      {toolsError && <p className="inline-error">{toolsError}</p>}
      <ToolList mcpTools={mcpTools} tools={tools} />
    </article>
  );
}
