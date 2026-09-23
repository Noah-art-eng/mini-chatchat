import type { ToolCatalogItem } from "./toolCatalog";
import { Icon } from "../ui";

type ToolCardProps = {
  isSelected: boolean;
  onSelect: (tool: ToolCatalogItem) => void;
  showDeveloperDetails: boolean;
  tool: ToolCatalogItem;
};

/** 用途：负责 ToolCard 的界面或数据处理职责。 */
export function ToolCard({
  isSelected,
  onSelect,
  showDeveloperDetails,
  tool
}: ToolCardProps) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <button
      aria-pressed={isSelected}
      className={[
        "tool-product-card",
        `tool-category-${tool.category}`,
        isSelected ? "selected" : ""
      ]
        .filter(Boolean)
        .join(" ")}
      onClick={() => onSelect(tool)}
      type="button"
    >
      <span className={`tool-product-icon icon-tone-${tool.iconTone}`} aria-hidden="true">
        <Icon icon={tool.icon} size="md" tone={tool.iconTone} />
      </span>
      <span className="tool-product-content">
        <strong>{tool.displayName}</strong>
        <span>{tool.shortDescription}</span>
        <small>{tool.example}</small>
      </span>
      <span className="tool-product-meta">
        <span>{tool.capability}</span>
      </span>
      {showDeveloperDetails && (
        <code translate="no">{tool.id}</code>
      )}
    </button>
  );
}
