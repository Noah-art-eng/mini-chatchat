import type { AgentRunResponse } from "../types/agent";

type AgentTracePanelProps = {
  error: string | null;
  isRunning: boolean;
  result: AgentRunResponse | null;
  streamStatus?: string | null;
  streamTokenText?: string;
};

function formatJson(value: unknown) {
  if (value === undefined || value === null) return "None";
  return JSON.stringify(value, null, 2);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asText(value: unknown) {
  return typeof value === "string" ? value : "";
}

function asNumber(value: unknown) {
  return typeof value === "number" ? value : null;
}

function getPreview(value: unknown, maxLength = 900) {
  const text = asText(value);
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}...`;
}

function renderCalculatorResult(result: Record<string, unknown>) {
  return (
    <div className="agent-tool-fields">
      <div>
        <span>Expression</span>
        <strong>{asText(result.expression) || "-"}</strong>
      </div>
      <div>
        <span>Result</span>
        <strong>{String(result.value ?? "-")}</strong>
      </div>
    </div>
  );
}

function renderKbSearchResult(result: Record<string, unknown>) {
  const sources = Array.isArray(result.sources) ? result.sources : [];

  return (
    <div className="agent-observation-list">
      {sources.length === 0 && <p className="muted">No sources returned.</p>}
      {sources.slice(0, 5).map((source, index) => {
        const item = isRecord(source) ? source : {};
        const score =
          asNumber(item.hybrid_score) ??
          asNumber(item.score) ??
          asNumber(item.distance);

        return (
          <article className="agent-observation-item" key={index}>
            <strong>{asText(item.source) || `Source ${index + 1}`}</strong>
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

function renderSqliteResult(result: Record<string, unknown>) {
  const columns = Array.isArray(result.columns) ? result.columns : [];
  const rows = Array.isArray(result.rows) ? result.rows : [];

  return (
    <div className="agent-sqlite-result">
      <div className="agent-tool-fields">
        <div>
          <span>Columns</span>
          <strong>{columns.map(String).join(", ") || "-"}</strong>
        </div>
        <div>
          <span>Rows</span>
          <strong>{String(result.row_count ?? rows.length)}</strong>
        </div>
        <div>
          <span>Truncated</span>
          <strong>{String(Boolean(result.truncated))}</strong>
        </div>
      </div>
      <pre>{formatJson(rows)}</pre>
    </div>
  );
}

function renderFilesystemResult(result: Record<string, unknown>) {
  return (
    <div className="agent-filesystem-result">
      <div className="agent-tool-fields">
        <div>
          <span>Path</span>
          <strong>{asText(result.path) || "-"}</strong>
        </div>
        <div>
          <span>Characters</span>
          <strong>{String(result.char_count ?? "-")}</strong>
        </div>
        <div>
          <span>Truncated</span>
          <strong>{String(Boolean(result.truncated))}</strong>
        </div>
      </div>
      <pre>{getPreview(result.content, 1600) || "No file content returned."}</pre>
    </div>
  );
}

function renderBrowserReadResult(result: Record<string, unknown>) {
  return (
    <div className="agent-browser-read-result">
      <div className="agent-tool-fields">
        <div>
          <span>Title</span>
          <strong>{asText(result.title) || "-"}</strong>
        </div>
        <div>
          <span>URL</span>
          <strong>{asText(result.url) || "-"}</strong>
        </div>
        <div>
          <span>Characters</span>
          <strong>{String(result.char_count ?? "-")}</strong>
        </div>
        <div>
          <span>Truncated</span>
          <strong>{String(Boolean(result.truncated))}</strong>
        </div>
      </div>
      <pre>{getPreview(result.text, 1600) || "No page text returned."}</pre>
    </div>
  );
}

function renderToolResult(toolName: string, value: unknown) {
  if (!isRecord(value)) {
    return <pre>{formatJson(value)}</pre>;
  }

  if (toolName === "calculator") {
    return renderCalculatorResult(value);
  }

  if (toolName === "kb_search") {
    return renderKbSearchResult(value);
  }

  if (toolName === "sqlite_readonly_query") {
    return renderSqliteResult(value);
  }

  if (toolName === "filesystem_readonly_read") {
    return renderFilesystemResult(value);
  }

  if (toolName === "browser_read") {
    return renderBrowserReadResult(value);
  }

  return <pre>{formatJson(value)}</pre>;
}

function getStepResultValue(stepResult: unknown) {
  if (!isRecord(stepResult)) return stepResult;
  return stepResult.result;
}

function getPlannerStatusIcon(status: string) {
  if (status === "running") return "▶";
  if (status === "completed") return "✓";
  if (status === "failed") return "✗";
  if (status === "skipped") return "○";
  return "☐";
}

function renderPlanner(result: AgentRunResponse) {
  const planner = result.planner;

  if (!planner) return null;

  return (
    <article
      className="agent-trace-card planner-card"
      data-testid="planner-panel"
    >
      <strong>Planning</strong>
      <div className="planner-summary">
        <span>Goal</span>
        <p data-testid="planner-goal">{planner.goal}</p>
      </div>
      <div className="agent-tool-fields">
        <div>
          <span>Status</span>
          <strong data-testid="planner-status">{planner.status}</strong>
        </div>
        <div>
          <span>Current Step</span>
          <strong>{String(planner.current_step ?? "-")}</strong>
        </div>
        <div>
          <span>Steps</span>
          <strong>{String(planner.steps.length)}</strong>
        </div>
      </div>
      <ol className="planner-step-list">
        {planner.steps.map(step => (
          <li
            className={`planner-step ${step.status}`}
            data-testid="planner-step"
            key={step.id}
          >
            <span aria-hidden="true">{getPlannerStatusIcon(step.status)}</span>
            <div>
              <strong>{`Step ${step.id}: ${step.title}`}</strong>
              <small>{step.status}</small>
              {step.observation && <p>{getPreview(step.observation, 300)}</p>}
            </div>
          </li>
        ))}
      </ol>
    </article>
  );
}

function renderAgentSteps(result: AgentRunResponse) {
  const steps = result.steps || [];

  if (steps.length === 0) return null;

  return (
    <>
      {steps.map(step => (
        <article
          className="agent-trace-card"
          data-testid="agent-step"
          key={step.step}
        >
          <strong>Step {step.step}</strong>
          <div data-testid="agent-step-tool">
            <strong>Tool Call</strong>
            <p>{step.tool_call.tool}</p>
            {step.tool_call.reason && <small>{step.tool_call.reason}</small>}
            <strong>Arguments</strong>
            <pre>{formatJson(step.tool_call.arguments)}</pre>
          </div>
          <div data-testid="agent-step-result">
            <strong>Tool Result</strong>
            <strong>Observation</strong>
            {step.tool_result.error && (
              <div className="agent-tool-error">
                <strong>Tool Error</strong>
                <p>{step.tool_result.error}</p>
              </div>
            )}
            {renderToolResult(
              step.tool_call.tool,
              getStepResultValue(step.tool_result)
            )}
          </div>
        </article>
      ))}
    </>
  );
}

export function AgentTracePanel({
  error,
  isRunning,
  result,
  streamStatus,
  streamTokenText = ""
}: AgentTracePanelProps) {
  if (!isRunning && !result && !error) return null;
  const hasSteps = Boolean(result?.steps?.length);

  return (
    <section
      aria-label="Agent trace"
      className="agent-trace-panel"
      data-testid="agent-trace-panel"
    >
      <div className="panel-heading">
        <p className="eyebrow">Agent Trace</p>
        <h3>{isRunning ? "Thinking..." : "Run Details"}</h3>
      </div>

      {streamStatus && (
        <article className="agent-trace-card" data-testid="agent-stream-status">
          <strong>{streamStatus}</strong>
        </article>
      )}

      {error && <p className="inline-error">{error}</p>}

      {result && renderPlanner(result)}

      {result && renderAgentSteps(result)}

      {!hasSteps && result?.tool_call && (
        <article className="agent-trace-card" data-testid="agent-tool-call">
          <strong>Selected Tool</strong>
          <p>{result.tool_call.tool}</p>
          {result.tool_call.reason && <small>{result.tool_call.reason}</small>}
          <strong>Tool Arguments</strong>
          <pre>{formatJson(result.tool_call.arguments)}</pre>
        </article>
      )}

      {!hasSteps && result?.tool_result && (
        <article className="agent-trace-card" data-testid="agent-tool-result">
          <strong>Tool Result / Observation</strong>
          {result.tool_result.error && (
            <div className="agent-tool-error">
              <strong>Tool Error</strong>
              <p>{result.tool_result.error}</p>
            </div>
          )}
          {renderToolResult(
            result.tool_call?.tool || "",
            result.tool_result.result
          )}
        </article>
      )}

      {result?.answer && (
        <article className="agent-trace-card" data-testid="agent-final-answer">
          <strong>Final Answer</strong>
          <p>{result.answer}</p>
        </article>
      )}

      {streamTokenText && (
        <article className="agent-trace-card" data-testid="agent-stream-token">
          <strong>Final Answer Token Streaming</strong>
          <p>{streamTokenText}</p>
        </article>
      )}

      {result?.trace && result.trace.length > 0 && (
        <article className="agent-trace-card">
          <strong>Trace</strong>
          <ol className="agent-trace-list">
            {result.trace.map((event, index) => (
              <li key={`${event.type || event.event || "event"}-${index}`}>
                <span>{event.type || event.event || "event"}</span>
                {event.step && <small>step {event.step}</small>}
                {event.tool && <small>{event.tool}</small>}
                {event.error && <small className="agent-error">{event.error}</small>}
              </li>
            ))}
          </ol>
        </article>
      )}
    </section>
  );
}
