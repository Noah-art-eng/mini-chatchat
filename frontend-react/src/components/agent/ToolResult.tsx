import type { AgentToolResult } from "../../types/agent";
import { Eye } from "lucide-react";
import {
  asNumber,
  asText,
  formatJson,
  getPreview,
  isRecord,
  type Translate
} from "./agentFormatters";
import { getToolVisualByName } from "./agentToolVisuals";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";

type ToolResultProps = {
  result: AgentToolResult;
  toolName: string;
};

/** 用途：负责 renderCalculatorResult 的界面或数据处理职责。 */
function renderCalculatorResult(result: Record<string, unknown>, t: Translate) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="agent-tool-fields">
      <div>
        <span>{t("agent.expression")}</span>
        <strong>{asText(result.expression) || "-"}</strong>
      </div>
      <div>
        <span>{t("agent.result")}</span>
        <strong>{String(result.value ?? "-")}</strong>
      </div>
    </div>
  );
}

/** 用途：负责 renderKbSearchResult 的界面或数据处理职责。 */
function renderKbSearchResult(result: Record<string, unknown>, t: Translate) {
  const sources = Array.isArray(result.sources) ? result.sources : [];

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="agent-observation-list">
      {sources.length === 0 && <p className="muted">{t("agent.noSources")}</p>}
      {sources.slice(0, 5).map((source, index) => {
        const item = isRecord(source) ? source : {};
        const score =
          /** 用途：负责 asNumber 的界面或数据处理职责。 */
          asNumber(item.hybrid_score) ??
          /** 用途：负责 asNumber 的界面或数据处理职责。 */
          asNumber(item.score) ??
          /** 用途：负责 asNumber 的界面或数据处理职责。 */
          asNumber(item.distance);

        /** 用途：负责 return 的界面或数据处理职责。 */
        return (
          <article className="agent-observation-item" key={index}>
            <strong>
              {asText(item.source) || t("sources.source", { index: index + 1 })}
            </strong>
            <small>
              chunk {String(item.chunk_id ?? index + 1)}
              {score !== null ? ` · score ${score.toFixed(3)}` : ""}
            </small>
            <p>{getPreview(item.chunk || item.content, 360)}</p>
          </article>
        );
      })}
    </div>
  );
}

/** 用途：负责 renderSqliteResult 的界面或数据处理职责。 */
function renderSqliteResult(result: Record<string, unknown>, t: Translate) {
  const columns = Array.isArray(result.columns) ? result.columns : [];
  const rows = Array.isArray(result.rows) ? result.rows : [];

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="agent-sqlite-result">
      <div className="agent-tool-fields">
        <div>
          <span>{t("agent.columns")}</span>
          <strong>{columns.map(String).join(", ") || "-"}</strong>
        </div>
        <div>
          <span>{t("agent.rows")}</span>
          <strong>{String(result.row_count ?? rows.length)}</strong>
        </div>
        <div>
          <span>{t("agent.truncated")}</span>
          <strong>{String(Boolean(result.truncated))}</strong>
        </div>
      </div>
      <pre>{formatJson(rows)}</pre>
    </div>
  );
}

/** 用途：负责 renderFilesystemResult 的界面或数据处理职责。 */
function renderFilesystemResult(result: Record<string, unknown>, t: Translate) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="agent-filesystem-result">
      <div className="agent-tool-fields">
        <div>
          <span>{t("agent.path")}</span>
          <strong>{asText(result.path) || "-"}</strong>
        </div>
        <div>
          <span>{t("agent.characters")}</span>
          <strong>{String(result.char_count ?? "-")}</strong>
        </div>
        <div>
          <span>{t("agent.truncated")}</span>
          <strong>{String(Boolean(result.truncated))}</strong>
        </div>
      </div>
      <pre>{getPreview(result.content, 1600) || t("agent.noFileContent")}</pre>
    </div>
  );
}

/** 用途：负责 renderBrowserReadResult 的界面或数据处理职责。 */
function renderBrowserReadResult(result: Record<string, unknown>, t: Translate) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="agent-browser-read-result">
      <div className="agent-tool-fields">
        <div>
          <span>{t("agent.title")}</span>
          <strong>{asText(result.title) || "-"}</strong>
        </div>
        <div>
          <span>{t("agent.url")}</span>
          <strong>{asText(result.url) || "-"}</strong>
        </div>
        <div>
          <span>{t("agent.characters")}</span>
          <strong>{String(result.char_count ?? "-")}</strong>
        </div>
        <div>
          <span>{t("agent.truncated")}</span>
          <strong>{String(Boolean(result.truncated))}</strong>
        </div>
      </div>
      <pre>{getPreview(result.text, 1600) || t("agent.noPageText")}</pre>
    </div>
  );
}

/** 用途：负责 renderBrowserSearchResult 的界面或数据处理职责。 */
function renderBrowserSearchResult(result: Record<string, unknown>, t: Translate) {
  const results = Array.isArray(result.results) ? result.results : [];

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="agent-observation-list">
      {results.length === 0 && <p className="muted">{t("agent.noSearchResults")}</p>}
      {results.slice(0, 5).map((item, index) => {
        const record = isRecord(item) ? item : {};
        const url = asText(record.url);

        /** 用途：负责 return 的界面或数据处理职责。 */
        return (
          <article className="agent-observation-item" key={`${url}-${index}`}>
            <strong>{asText(record.title) || t("sources.source", { index: index + 1 })}</strong>
            {url && (
              <a href={url} rel="noopener noreferrer" target="_blank">
                {url}
              </a>
            )}
            <p>{getPreview(record.snippet, 360)}</p>
          </article>
        );
      })}
    </div>
  );
}

/** 用途：负责 renderToolResultByName 的界面或数据处理职责。 */
function renderToolResultByName(
  toolName: string,
  value: unknown,
  t: Translate
) {
  if (!isRecord(value)) {
    return <pre>{formatJson(value)}</pre>;
  }

  if (toolName === "calculator") return renderCalculatorResult(value, t);
  if (toolName === "kb_search") return renderKbSearchResult(value, t);
  if (toolName === "sqlite_readonly_query") return renderSqliteResult(value, t);
  if (toolName === "filesystem_readonly_read") return renderFilesystemResult(value, t);
  if (toolName === "browser_read") return renderBrowserReadResult(value, t);
  if (toolName === "browser_search") return renderBrowserSearchResult(value, t);

  return <pre>{formatJson(value)}</pre>;
}

/** 用途：负责 ToolResult 的界面或数据处理职责。 */
export function ToolResult({ result, toolName }: ToolResultProps) {
  const { t } = useI18n();
  const toolVisual = getToolVisualByName(toolName);

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div data-testid="agent-step-result">
      <strong className="agent-card-title">
        <Icon icon={toolName ? toolVisual.icon : Eye} size="sm" tone={toolVisual.tone} />
        {t("agent.observation")}
      </strong>
      {result.error && (
        <div className="agent-tool-error">
          <strong>{t("agent.toolError")}</strong>
          <p>{result.error}</p>
        </div>
      )}
      <details className="agent-observation-detail">
        <summary>
          {result.error ? t("agent.viewFailedObservation") : t("agent.viewObservation")}
        </summary>
        {renderToolResultByName(toolName, result.result, t)}
      </details>
      {result.metadata && (
        <details className="agent-metadata-detail">
          <summary>Metadata</summary>
          <pre>{formatJson(result.metadata)}</pre>
        </details>
      )}
    </div>
  );
}
