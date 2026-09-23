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
    <div className="tool-center">
      <section className="tool-center-intro">
        <p className="eyebrow">{t("tools.title")}</p>
        <h3>{t("tools.introTitle")}</h3>
        <p>{t("tools.introDescription")}</p>
        <p className="muted">{t("tools.introHowToUse")}</p>
      </section>

      <div className="tool-center-controls">
        <label className="tool-search-field">
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

        <div className="tool-filter-list" aria-label={t("tools.filterLabel")}>
          {categoryFilters.map(category => (
            <button
              aria-pressed={activeFilter === category}
              className={activeFilter === category ? "active" : ""}
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
        <div className="tool-empty-state">
          <strong>{t("tools.emptyTitle")}</strong>
          <p>{t("tools.emptyDescription")}</p>
        </div>
      )}

      {recommendedTools.length > 0 && activeFilter !== "mcp" && (
        <section className="tool-section" aria-label={t("tools.recommended")}>
          <div className="tool-section-heading">
            <h3>{t("tools.recommended")}</h3>
            <p>{t("tools.recommendedDescription")}</p>
          </div>
          <div className="system-tool-list">
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
        <section className="tool-section" key={section.category}>
          <div className="tool-section-heading">
            <h3>{t(getCategoryLabelKey(section.category))}</h3>
            <p>{t(getCategoryDescriptionKey(section.category))}</p>
          </div>
          <div className="system-tool-list">
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
        <aside className="tool-detail-drawer" aria-label={t("tools.detailTitle")}>
          <div className="tool-detail-header">
            <span
              className={`tool-product-icon icon-tone-${selectedTool.iconTone}`}
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

          <dl className="tool-detail-list">
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
            <details className="tool-schema-detail">
              <summary>{t("tools.schema")}</summary>
              <pre>{JSON.stringify(getSchema(selectedTool), null, 2)}</pre>
            </details>
          )}

          <div className="tool-example-box">
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
