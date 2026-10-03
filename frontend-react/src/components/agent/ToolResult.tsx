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
import { agentStyles } from "./agentStyles";

type ToolResultProps = {
  result: AgentToolResult;
  toolName: string;
};

function renderCalculatorResult(result: Record<string, unknown>, t: Translate) {
  return (
    <div className={agentStyles.fields}>
      <div className={agentStyles.field}>
        <span>{t("agent.expression")}</span>
        <strong>{asText(result.expression) || "-"}</strong>
      </div>
      <div className={agentStyles.field}>
        <span>{t("agent.result")}</span>
        <strong>{String(result.value ?? "-")}</strong>
      </div>
    </div>
  );
}

function renderKbSearchResult(result: Record<string, unknown>, t: Translate) {
  const sources = Array.isArray(result.sources) ? result.sources : [];

  return (
    <div className={agentStyles.observationList}>
      {sources.length === 0 && <p className="muted">{t("agent.noSources")}</p>}
      {sources.slice(0, 5).map((source, index) => {
        const item = isRecord(source) ? source : {};
        const score =
          asNumber(item.hybrid_score) ??
          asNumber(item.score) ??
          asNumber(item.distance);

        return (
          <article className={agentStyles.observationItem} key={index}>
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

function renderSqliteResult(result: Record<string, unknown>, t: Translate) {
  const columns = Array.isArray(result.columns) ? result.columns : [];
  const rows = Array.isArray(result.rows) ? result.rows : [];

  return (
    <div className="agent-sqlite-result">
      <div className={agentStyles.fields}>
        <div className={agentStyles.field}>
          <span>{t("agent.columns")}</span>
          <strong>{columns.map(String).join(", ") || "-"}</strong>
        </div>
        <div className={agentStyles.field}>
          <span>{t("agent.rows")}</span>
          <strong>{String(result.row_count ?? rows.length)}</strong>
        </div>
        <div className={agentStyles.field}>
          <span>{t("agent.truncated")}</span>
          <strong>{String(Boolean(result.truncated))}</strong>
        </div>
      </div>
      <pre>{formatJson(rows)}</pre>
    </div>
  );
}

function renderFilesystemResult(result: Record<string, unknown>, t: Translate) {
  return (
    <div className="agent-filesystem-result">
      <div className={agentStyles.fields}>
        <div className={agentStyles.field}>
          <span>{t("agent.path")}</span>
          <strong>{asText(result.path) || "-"}</strong>
        </div>
        <div className={agentStyles.field}>
          <span>{t("agent.characters")}</span>
          <strong>{String(result.char_count ?? "-")}</strong>
        </div>
        <div className={agentStyles.field}>
          <span>{t("agent.truncated")}</span>
          <strong>{String(Boolean(result.truncated))}</strong>
        </div>
      </div>
      <pre>{getPreview(result.content, 1600) || t("agent.noFileContent")}</pre>
    </div>
  );
}

function renderBrowserReadResult(result: Record<string, unknown>, t: Translate) {
  return (
    <div className="agent-browser-read-result">
      <div className={agentStyles.fields}>
        <div className={agentStyles.field}>
          <span>{t("agent.title")}</span>
          <strong>{asText(result.title) || "-"}</strong>
        </div>
        <div className={agentStyles.field}>
          <span>{t("agent.url")}</span>
          <strong>{asText(result.url) || "-"}</strong>
        </div>
        <div className={agentStyles.field}>
          <span>{t("agent.characters")}</span>
          <strong>{String(result.char_count ?? "-")}</strong>
        </div>
        <div className={agentStyles.field}>
          <span>{t("agent.truncated")}</span>
          <strong>{String(Boolean(result.truncated))}</strong>
        </div>
      </div>
      <pre>{getPreview(result.text, 1600) || t("agent.noPageText")}</pre>
    </div>
  );
}

function renderBrowserSearchResult(result: Record<string, unknown>, t: Translate) {
  const results = Array.isArray(result.results) ? result.results : [];

  return (
    <div className={agentStyles.observationList}>
      {results.length === 0 && <p className="muted">{t("agent.noSearchResults")}</p>}
      {results.slice(0, 5).map((item, index) => {
        const record = isRecord(item) ? item : {};
        const url = asText(record.url);

        return (
          <article className={agentStyles.observationItem} key={`${url}-${index}`}>
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

export function ToolResult({ result, toolName }: ToolResultProps) {
  const { t } = useI18n();
  const toolVisual = getToolVisualByName(toolName);

  return (
    <div data-testid="agent-step-result">
      <strong className={agentStyles.title}>
        <Icon icon={toolName ? toolVisual.icon : Eye} size="sm" tone={toolVisual.tone} />
        {t("agent.observation")}
      </strong>
      {result.error && (
        <div className={agentStyles.toolError}>
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
