import { useMemo, useState } from "react";
import { X } from "lucide-react";
import { ToolCard } from "./ToolCard";
import {
  isRecommendedTool,
  toToolCatalogItem,
  toolCategoryOrder,
  type ToolCatalogItem,
  type ToolCategory
} from "./toolCatalog";
import { useI18n } from "../../i18n";
import {
  isDeveloperModeIntroSeen,
  setDeveloperModeIntroSeen
} from "../../onboarding/preferences";
import { DeveloperModeIntroDialog } from "../onboarding";
import { Icon, IconButton } from "../ui";
import { cx } from "../ui/utils";
import type { ToolSpecResponse } from "../../api/system";

type ToolListProps = {
  mcpTools?: ToolSpecResponse[];
  tools: ToolSpecResponse[];
};

const categoryFilters: ToolCategory[] = [
  "all",
  "recommended",
  "knowledge",
  "files",
  "network",
  "database",
  "mcp",
  "system"
];

/** 用途：负责 getCategoryLabelKey 的界面或数据处理职责。 */
function getCategoryLabelKey(category: ToolCategory) {
  if (category === "all") return "tools.filterAll";
  if (category === "recommended") return "tools.filterRecommended";
  if (category === "knowledge") return "tools.categoryKnowledge";
  if (category === "files") return "tools.categoryFiles";
  if (category === "network") return "tools.categoryNetwork";
  if (category === "database") return "tools.categoryDatabase";
  if (category === "mcp") return "tools.categoryMcp";
  return "tools.categorySystem";
}

/** 用途：负责 getCategoryDescriptionKey 的界面或数据处理职责。 */
function getCategoryDescriptionKey(category: ToolCatalogItem["category"]) {
  if (category === "knowledge") return "tools.categoryKnowledgeDescription";
  if (category === "files") return "tools.categoryFilesDescription";
  if (category === "network") return "tools.categoryNetworkDescription";
  if (category === "database") return "tools.categoryDatabaseDescription";
  if (category === "mcp") return "tools.categoryMcpDescription";
  return "tools.categorySystemDescription";
}

/** 用途：负责 dedupeTools 的界面或数据处理职责。 */
function dedupeTools(tools: ToolSpecResponse[]) {
  const seen = new Set<string>();
  return tools.filter(tool => {
    const id = tool.qualified_name || tool.name;
    if (seen.has(id)) return false;
    seen.add(id);
    return true;
  });
}

/** 用途：负责 getSchema 的界面或数据处理职责。 */
function getSchema(tool: ToolCatalogItem) {
  return tool.spec.args_schema || tool.spec.input_schema || {};
}

/** 用途：负责 ToolList 的界面或数据处理职责。 */
export function ToolList({ mcpTools = [], tools }: ToolListProps) {
  const { t } = useI18n();
  const [activeFilter, setActiveFilter] = useState<ToolCategory>("all");
  const [query, setQuery] = useState("");
  const [selectedTool, setSelectedTool] = useState<ToolCatalogItem | null>(null);
  const [isDeveloperMode, setIsDeveloperMode] = useState(false);
  const [isDeveloperIntroOpen, setIsDeveloperIntroOpen] = useState(false);

  const catalogItems = useMemo(
    () => dedupeTools([...tools, ...mcpTools]).map(tool => toToolCatalogItem(tool, t)),
    [mcpTools, t, tools]
  );

  const normalizedQuery = query.trim().toLowerCase();
  const filteredItems = catalogItems.filter(tool => {
    const matchesQuery =
      normalizedQuery.length === 0 || tool.searchText.includes(normalizedQuery);
    const matchesFilter =
      activeFilter === "all" ||
      (activeFilter === "recommended" && isRecommendedTool(tool)) ||
      tool.category === activeFilter;

    return matchesQuery && matchesFilter;
  });

  const recommendedTools = filteredItems
    .filter(isRecommendedTool)
    .slice(0, 6);
  const sectionItems = toolCategoryOrder
    .map(category => ({
      category,
      items: filteredItems.filter(tool => tool.category === category)
    }))
    .filter(section => section.items.length > 0);

  if (catalogItems.length === 0) {
    return <p className="muted">{t("settings.noTools")}</p>;
  }

  /** 用途：负责 toggleDeveloperMode 的界面或数据处理职责。 */
  function toggleDeveloperMode() {
    if (isDeveloperMode) {
      /** 用途：负责 setIsDeveloperMode 的界面或数据处理职责。 */
      setIsDeveloperMode(false);
      return;
    }

    if (isDeveloperModeIntroSeen()) {
      /** 用途：负责 setIsDeveloperMode 的界面或数据处理职责。 */
      setIsDeveloperMode(true);
      return;
    }

    /** 用途：负责 setIsDeveloperIntroOpen 的界面或数据处理职责。 */
    setIsDeveloperIntroOpen(true);
  }

  /** 用途：负责 confirmDeveloperMode 的界面或数据处理职责。 */
  function confirmDeveloperMode() {
    /** 用途：负责 setDeveloperModeIntroSeen 的界面或数据处理职责。 */
    setDeveloperModeIntroSeen(true);
    /** 用途：负责 setIsDeveloperMode 的界面或数据处理职责。 */
    setIsDeveloperMode(true);
    /** 用途：负责 setIsDeveloperIntroOpen 的界面或数据处理职责。 */
    setIsDeveloperIntroOpen(false);
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="tool-center relative grid min-w-0 gap-mc-6">
      <section className="tool-center-intro grid gap-mc-2 rounded-mc-xl border border-solid border-mc-border-subtle bg-[color-mix(in_srgb,var(--color-brand-soft)_48%,var(--color-bg-surface))] p-mc-5 [&_h3]:m-0 [&_p]:m-0">
        <p className="eyebrow">{t("tools.title")}</p>
        <h3>{t("tools.introTitle")}</h3>
        <p>{t("tools.introDescription")}</p>
        <p className="muted">{t("tools.introHowToUse")}</p>
      </section>

      <div className="tool-center-controls grid grid-cols-[minmax(220px,320px)_minmax(0,1fr)_auto] items-end gap-mc-3 max-[1100px]:grid-cols-1">
        <label className="tool-search-field grid gap-mc-2 [&>span]:text-mc-label [&>span]:font-mc-semibold [&>span]:text-mc-secondary [&>input]:min-h-[var(--control-height-md)] [&>input]:rounded-mc-pill">
          <span>{t("tools.searchLabel")}</span>
          <input
            autoComplete="off"
            name="tool-search"
            onChange={event => setQuery(event.target.value)}
            placeholder={t("tools.searchPlaceholder")}
            type="search"
            value={query}
          />
        </label>

        <div className="tool-filter-list flex flex-wrap gap-mc-2" aria-label={t("tools.filterLabel")}>
          {categoryFilters.map(category => (
            <button
              aria-pressed={activeFilter === category}
              className={cx(
                "min-h-[var(--control-height-sm)] rounded-mc-pill border border-solid border-mc-border-subtle px-mc-3 [padding-block:0px] text-mc-body-small leading-[normal] font-mc-medium transition-[background-color,border-color,color] duration-[var(--motion-duration-fast)] ease-[var(--motion-ease-standard)] hover:bg-mc-hover hover:text-mc-text focus-visible:[box-shadow:var(--shadow-focus)]",
                activeFilter === category
                  ? "active bg-mc-brand-soft text-mc-brand-active"
                  : "bg-transparent text-mc-secondary"
              )}
              key={category}
              onClick={() => setActiveFilter(category)}
              type="button"
            >
              {t(getCategoryLabelKey(category))}
            </button>
          ))}
        </div>

        <button
          aria-pressed={isDeveloperMode}
          className={isDeveloperMode ? "developer-toggle active" : "developer-toggle"}
          onClick={toggleDeveloperMode}
          type="button"
        >
          {t("chat.developerMode")}
        </button>
      </div>

      {filteredItems.length === 0 && (
        <div className="tool-empty-state rounded-mc-lg border border-dashed border-mc-border bg-mc-subtle p-mc-6 text-center text-mc-secondary [&_p]:m-0 [&_strong]:m-0">
          <strong>{t("tools.emptyTitle")}</strong>
          <p>{t("tools.emptyDescription")}</p>
        </div>
      )}

      {recommendedTools.length > 0 && activeFilter !== "mcp" && (
        <section className="tool-section grid gap-mc-3" aria-label={t("tools.recommended")}>
          <div className="tool-section-heading flex items-end justify-between gap-mc-4 max-[720px]:flex-col max-[720px]:items-start [&_h3]:m-0 [&_h3]:text-mc-title [&_p]:m-0 [&_p]:max-w-[560px] [&_p]:text-mc-body-small [&_p]:text-mc-secondary">
            <h3>{t("tools.recommended")}</h3>
            <p>{t("tools.recommendedDescription")}</p>
          </div>
          <div className="system-tool-list grid grid-cols-[repeat(auto-fill,minmax(210px,1fr))] gap-mc-4 max-[1100px]:grid-cols-[repeat(auto-fill,minmax(220px,1fr))] max-[720px]:grid-cols-1">
            {recommendedTools.map(tool => (
              <ToolCard
                isSelected={selectedTool?.id === tool.id}
                key={`recommended-${tool.id}`}
                onSelect={setSelectedTool}
                showDeveloperDetails={isDeveloperMode}
                tool={tool}
              />
            ))}
          </div>
        </section>
      )}

      {sectionItems.map(section => (
        <section className="tool-section grid gap-mc-3" key={section.category}>
          <div className="tool-section-heading flex items-end justify-between gap-mc-4 max-[720px]:flex-col max-[720px]:items-start [&_h3]:m-0 [&_h3]:text-mc-title [&_p]:m-0 [&_p]:max-w-[560px] [&_p]:text-mc-body-small [&_p]:text-mc-secondary">
            <h3>{t(getCategoryLabelKey(section.category))}</h3>
            <p>{t(getCategoryDescriptionKey(section.category))}</p>
          </div>
          <div className="system-tool-list grid grid-cols-[repeat(auto-fill,minmax(210px,1fr))] gap-mc-4 max-[1100px]:grid-cols-[repeat(auto-fill,minmax(220px,1fr))] max-[720px]:grid-cols-1">
            {section.items.map(tool => (
              <ToolCard
                isSelected={selectedTool?.id === tool.id}
                key={tool.id}
                onSelect={setSelectedTool}
                showDeveloperDetails={isDeveloperMode}
                tool={tool}
              />
            ))}
          </div>
        </section>
      ))}

      {selectedTool && (
        <aside className="tool-detail-drawer fixed top-[calc(var(--topbar-height)+var(--space-6))] right-mc-6 z-[var(--z-dropdown)] grid max-h-[min(720px,82vh)] w-[min(420px,calc(100vw-var(--space-12)))] gap-mc-4 overflow-y-auto rounded-mc-xl border border-solid border-mc-border-subtle bg-[color-mix(in_srgb,var(--color-bg-surface)_86%,transparent)] p-mc-5 shadow-mc-md [backdrop-filter:blur(18px)] max-[720px]:top-auto max-[720px]:right-0 max-[720px]:bottom-0 max-[720px]:left-0 max-[720px]:max-h-[var(--bottom-sheet-max-height)] max-[720px]:w-full max-[720px]:rounded-t-mc-xl max-[720px]:rounded-b-none" aria-label={t("tools.detailTitle")}>
          <div className="tool-detail-header grid grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-mc-3 [&_h3]:m-0">
            <span
              className="tool-product-icon inline-flex h-[var(--icon-container-md)] w-[var(--icon-container-md)] flex-none items-center justify-center rounded-mc-md border border-solid border-mc-border-subtle bg-mc-elevated"
              aria-hidden="true"
            >
              <Icon icon={selectedTool.icon} size="md" tone={selectedTool.iconTone} />
            </span>
            <div>
              <p className="eyebrow">{selectedTool.capability}</p>
              <h3>{selectedTool.displayName}</h3>
            </div>
            <IconButton
              aria-label={t("common.close")}
              onClick={() => setSelectedTool(null)}
              type="button"
            >
              <Icon icon={X} size="sm" />
            </IconButton>
          </div>

          <p>{selectedTool.fullDescription}</p>

          <dl className="tool-detail-list m-0 grid gap-mc-3 [&>div]:grid [&>div]:gap-mc-1 [&>div]:border-t [&>div]:border-solid [&>div]:border-mc-border-subtle [&>div]:pt-mc-3 [&_dt]:text-mc-caption [&_dt]:font-mc-semibold [&_dt]:text-mc-muted [&_dd]:m-0 [&_dd]:text-mc-body-small [&_dd]:text-mc-text [&_dd]:[overflow-wrap:anywhere]">
            <div>
              <dt>{t("tools.capability")}</dt>
              <dd>{isDeveloperMode ? selectedTool.capability : selectedTool.displayName}</dd>
            </div>
            {isDeveloperMode && (
              <>
                <div>
                  <dt>{t("tools.provider")}</dt>
                  <dd>{selectedTool.providerLabel}</dd>
                </div>
                <div>
                  <dt>{t("tools.toolId")}</dt>
                  <dd>
                    <code translate="no">{selectedTool.id}</code>
                  </dd>
                </div>
                <div>
                  <dt>{t("tools.risk")}</dt>
                  <dd>{selectedTool.spec.risk_level || "low"}</dd>
                </div>
              </>
            )}
          </dl>

          {isDeveloperMode && (
            <details className="tool-schema-detail rounded-mc-md border border-solid border-mc-border-subtle p-mc-3 [&>summary]:cursor-pointer [&>summary]:font-mc-semibold">
              <summary>{t("tools.schema")}</summary>
              <pre>{JSON.stringify(getSchema(selectedTool), null, 2)}</pre>
            </details>
          )}

          <div className="tool-example-box grid gap-mc-1 rounded-mc-lg bg-mc-subtle p-mc-4 [&_p]:m-0 [&_strong]:m-0">
            <strong>{t("tools.example")}</strong>
            <p>{selectedTool.example}</p>
          </div>
        </aside>
      )}
      <DeveloperModeIntroDialog
        isOpen={isDeveloperIntroOpen}
        onCancel={() => setIsDeveloperIntroOpen(false)}
        onConfirm={confirmDeveloperMode}
      />
    </div>
  );
}
