import os
import sys

import requests


API_BASE = os.getenv(
    "MINI_CHATCHAT_API_BASE",
    "http://127.0.0.1:8000",
).rstrip("/")

FORBIDDEN_TEXT = (
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "invalid_api_key",
    "OpenAI 401",
)


def pass_step(message):
    print(f"[PASS] {message}")


def fail_step(message, response=None):
    print(f"[FAIL] {message}")

    if response is not None:
        print(f"status={response.status_code}")
        print(f"body={response.text[:1600]}")

    sys.exit(1)


def request(method, path, **kwargs):
    try:
        return requests.request(
            method,
            f"{API_BASE}{path}",
            timeout=120,
            **kwargs,
        )
    except requests.ConnectionError:
        fail_step(f"Backend is not running at {API_BASE}")
    except requests.RequestException as exc:
        print(f"[FAIL] request failed: {method} {path}")
        print(exc)
        sys.exit(1)


def assert_safe_response(response, step_name):
    for text in FORBIDDEN_TEXT:
        if text.lower() in response.text.lower():
            fail_step(f"{step_name}: forbidden text found: {text}", response)


def expect_ok_json(response, step_name):
    assert_safe_response(response, step_name)

    if response.status_code != 200:
        fail_step(f"{step_name}: HTTP status is not 200", response)

    try:
        return response.json()
    except ValueError:
        fail_step(f"{step_name}: response is not JSON", response)


def check_tool_is_listed():
    response = request("GET", "/agent/tools")
    data = expect_ok_json(response, "GET /agent/tools")

    tools = data.get("tools") or []
    names = {
        tool.get("name")
        for tool in tools
    }

    if "sqlite_readonly_query" not in names:
        fail_step("sqlite_readonly_query missing from tool registry", response)

    print(f"tools summary={sorted(names)}")
    pass_step("GET /agent/tools includes sqlite_readonly_query")


def check_direct_select():
    response = request(
        "POST",
        "/agent/tools/sqlite_readonly_query/run",
        json={
            "arguments": {
                "sql": "SELECT COUNT(*) AS count FROM conversation",
                "limit": 5,
            }
        },
    )
    data = expect_ok_json(response, "POST sqlite_readonly_query SELECT")

    if not data.get("ok"):
        fail_step("sqlite SELECT returned ok=false", response)

    result = data.get("result") or {}
    columns = result.get("columns") or []
    rows = result.get("rows") or []

    if "count" not in columns or not rows:
        fail_step("sqlite SELECT missing count result", response)

    print(
        "sqlite SELECT summary="
        f"columns={columns}, rows={rows}, row_count={result.get('row_count')}"
    )
    pass_step("POST /agent/tools/sqlite_readonly_query/run SELECT")


def check_direct_write_rejected():
    response = request(
        "POST",
        "/agent/tools/sqlite_readonly_query/run",
        json={
            "arguments": {
                "sql": "UPDATE conversation SET title = 'bad'",
            }
        },
    )
    data = expect_ok_json(response, "POST sqlite_readonly_query UPDATE")

    if data.get("ok"):
        fail_step("sqlite UPDATE should be rejected", response)

    error = data.get("error") or ""
    if "SELECT" not in error and "not allowed" not in error:
        fail_step("sqlite UPDATE rejection message is not clear", response)

    print(f"sqlite UPDATE summary=error={error!r}")
    pass_step("POST /agent/tools/sqlite_readonly_query/run rejects UPDATE")


def check_agent_run_sqlite():
    response = request(
        "POST",
        "/agent/run",
        json={
            "query": (
                "Use sqlite_readonly_query to run this exact SQL: "
                "SELECT COUNT(*) AS count FROM conversation"
            ),
            "kb_name": "default",
            "tools": ["sqlite_readonly_query"],
        },
    )
    data = expect_ok_json(response, "POST /agent/run sqlite_readonly_query")

    if data.get("error"):
        fail_step("agent sqlite returned unexpected error", response)

    tool_call = data.get("tool_call") or {}
    tool_result = data.get("tool_result") or {}

    if tool_call.get("tool") != "sqlite_readonly_query":
        fail_step("agent did not choose sqlite_readonly_query", response)

    if not tool_result.get("ok"):
        fail_step("agent sqlite tool_result ok=false", response)

    rows = ((tool_result.get("result") or {}).get("rows")) or []
    if not rows or "count" not in rows[0]:
        fail_step("agent sqlite result missing count row", response)

    answer = data.get("answer") or ""
    if not answer.strip():
        fail_step("agent sqlite final answer missing", response)

    print(
        "agent sqlite summary="
        f"tool={tool_call.get('tool')}, rows={rows}, answer={answer[:120]!r}"
    )
    pass_step("POST /agent/run sqlite_readonly_query")


def main():
    print(f"API_BASE={API_BASE}")
    check_tool_is_listed()
    check_direct_select()
    check_direct_write_rejected()
    check_agent_run_sqlite()
    pass_step("SQLite readonly tool smoke test complete")


if __name__ == "__main__":
    main()
