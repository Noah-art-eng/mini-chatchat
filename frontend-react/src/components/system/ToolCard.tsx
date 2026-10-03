import type { ToolCatalogItem } from "./toolCatalog";
import { Icon } from "../ui";
import { cx } from "../ui/utils";

type ToolCardProps = {
  isSelected: boolean;
  onSelect: (tool: ToolCatalogItem) => void;
  showDeveloperDetails: boolean;
  tool: ToolCatalogItem;
};

const categoryClasses: Record<ToolCatalogItem["category"], string> = {
  knowledge: "[--tool-card-tint:var(--color-brand-soft)] [--tool-icon-color:var(--icon-tone-knowledge)]",
  files: "[--tool-card-tint:var(--icon-tone-file-soft)] [--tool-icon-color:var(--icon-tone-file)]",
  network: "[--tool-card-tint:var(--color-accent-soft)] [--tool-icon-color:var(--color-accent-primary)]",
  database: "[--tool-card-tint:var(--icon-tone-database-soft)] [--tool-icon-color:var(--icon-tone-database)]",
  mcp: "[--tool-card-tint:var(--color-brand-soft)] [--tool-icon-color:var(--icon-tone-mcp)]",
  system: "[--tool-card-tint:var(--color-brand-soft)] [--tool-icon-color:var(--icon-tone-system)]"
};

export function ToolCard({
  isSelected,
  onSelect,
  showDeveloperDetails,
  tool
}: ToolCardProps) {
  return (
    <button
      aria-pressed={isSelected}
      className={cx(
        "tool-product-card grid min-h-[184px] items-start gap-mc-3 rounded-mc-lg border border-solid border-mc-border-subtle bg-[color-mix(in_srgb,var(--color-bg-surface)_86%,transparent)] p-mc-4 text-left text-mc-text [box-shadow:none] [backdrop-filter:blur(18px)] transition-[background-color,border-color,transform] duration-[var(--motion-duration-fast)] ease-[var(--motion-ease-standard)] hover:-translate-y-[2px] hover:border-mc-border hover:bg-mc-elevated",
        categoryClasses[tool.category],
        isSelected && "selected -translate-y-[2px] border-mc-border bg-mc-elevated"
      )}
      onClick={() => onSelect(tool)}
      type="button"
    >
      <span className="tool-product-icon inline-flex h-[var(--icon-container-md)] w-[var(--icon-container-md)] flex-none items-center justify-center rounded-mc-md border border-solid border-mc-border-subtle bg-[color-mix(in_srgb,var(--color-bg-elevated)_72%,var(--tool-card-tint,var(--color-bg-subtle)))] text-[var(--tool-icon-color,var(--color-brand-primary))]" aria-hidden="true">
        <Icon icon={tool.icon} size="md" tone={tool.iconTone} />
      </span>
      <span className="tool-product-content grid min-w-0 gap-mc-1 [&>strong]:[overflow-wrap:anywhere] [&>strong]:text-mc-body [&>strong]:leading-[var(--line-height-compact)] [&>span]:text-mc-body-small [&>span]:text-mc-secondary [&>small]:text-mc-caption [&>small]:text-mc-muted">
        <strong>{tool.displayName}</strong>
        <span>{tool.shortDescription}</span>
        <small>{tool.example}</small>
      </span>
      <span className="tool-product-meta flex flex-wrap gap-mc-2 [&>span]:rounded-mc-pill [&>span]:bg-[color-mix(in_srgb,var(--color-bg-elevated)_70%,var(--tool-card-tint,var(--color-bg-subtle)))] [&>span]:px-mc-2 [&>span]:py-mc-1 [&>span]:text-mc-badge [&>span]:font-mc-semibold [&>span]:text-mc-muted">
        <span>{tool.capability}</span>
      </span>
      {showDeveloperDetails && (
        <code className="font-mc-mono text-[11px] text-mc-muted [overflow-wrap:anywhere]" translate="no">{tool.id}</code>
      )}
    </button>
  );
}
