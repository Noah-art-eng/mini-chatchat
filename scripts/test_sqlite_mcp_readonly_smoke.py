import os
import sys

import requests

from smoke_auth import auth_headers


API_BASE = os.getenv(
    "MINI_CHATCHAT_API_BASE",
    "http://127.0.0.1:8000",
).rstrip("/")

FORBIDDEN_TEXT = (
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "invalid_api_key",
    "OpenAI 401",
    "MCP command",
    "stderr",
)
BLOCKED_PUBLIC_KEYS = {"command", "cmd", "cwd", "args", "env", "environment", "stderr", "stdout"}


def pass_step(message):
    """负责 pass_step 的函数职责。"""
    print(f"[PASS] {message}")


def fail_step(message, response=None):
    """负责 fail_step 的函数职责。"""
    print(f"[FAIL] {message}")

    if response is not None:
        print(f"status={response.status_code}")
        print(f"body={response.text[:3000]}")

    sys.exit(1)


def request(method, path, **kwargs):
    """负责 request 的函数职责。"""
    headers = kwargs.pop("headers", {})
    headers = {**auth_headers(), **headers}

    try:
        return requests.request(
            method,
            f"{API_BASE}{path}",
            headers=headers,
            timeout=240,
            **kwargs,
        )
    except requests.ConnectionError:
        fail_step(f"Backend is not running at {API_BASE}")
    except requests.RequestException as exc:
        print(f"[FAIL] request failed: {method} {path}")
        print(exc)
        sys.exit(1)


def assert_safe_response(response, step_name):
    """负责 assert_safe_response 的函数职责。"""
    lower = response.text.lower()
    for text in FORBIDDEN_TEXT:
        if text.lower() in lower:
            fail_step(f"{step_name}: forbidden text found: {text}", response)


def expect_ok_json(response, step_name):
    """负责 expect_ok_json 的函数职责。"""
    assert_safe_response(response, step_name)

    if response.status_code != 200:
        fail_step(f"{step_name}: HTTP status is not 200", response)

    try:
        data = response.json()
    except ValueError:
        fail_step(f"{step_name}: response is not JSON", response)

    assert_no_public_leaks(data, step_name)
    return data


def assert_no_public_leaks(value, step_name):
    """负责 assert_no_public_leaks 的函数职责。"""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in BLOCKED_PUBLIC_KEYS:
                fail_step(f"{step_name}: leaked {key}")
            assert_no_public_leaks(child, step_name)
    elif isinstance(value, list):
        for child in value:
            assert_no_public_leaks(child, step_name)


def assert_sqlite_metadata(data, response, tool_name):
    """负责 assert_sqlite_metadata 的函数职责。"""
    metadata = data.get("metadata") or {}
    expected = {
        "provider": "mcp",
        "server": "sqlite",
        "tool": tool_name,
        "server_name": "sqlite",
        "tool_name": tool_name,
        "read_only": True,
        "risk_level": "low",
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            fail_step(f"metadata mismatch for {key}", response)


def check_sqlite_discovery():
    """负责 check_sqlite_discovery 的函数职责。"""
    response = request("GET", "/agent/mcp/servers")
    data = expect_ok_json(response, "GET /agent/mcp/servers")
    servers = data.get("servers") or []
    sqlite = next((item for item in servers if item.get("server") == "sqlite"), None)
    if not sqlite:
        fail_step("sqlite MCP server missing", response)

    response = request("GET", "/agent/mcp/tools")
    data = expect_ok_json(response, "GET /agent/mcp/tools")
    tools = data.get("tools") or []
    names = {tool.get("qualified_name") for tool in tools}
    required = {
        "mcp.sqlite.query",
        "mcp.sqlite.list-tables",
        "mcp.sqlite.describe-table",
    }
    missing = required - names
    if missing:
        fail_step(f"sqlite MCP tools missing {sorted(missing)}", response)

    forbidden = {
        name
        for name in names
        if name.startswith("mcp.sqlite.")
        and name not in required
    }
    if forbidden:
        fail_step(f"write-capable sqlite MCP tools were registered: {sorted(forbidden)}", response)

    for tool in tools:
        if tool.get("qualified_name") in required:
            if tool.get("provider") != "mcp":
                fail_step("sqlite MCP provider mismatch", response)
            if tool.get("read_only") is not True or tool.get("risk_level") != "low":
                fail_step("sqlite MCP safety metadata invalid", response)

    print(f"sqlite discovery summary={sorted(required)}")
    pass_step("SQLite MCP initialize and tools/list")


def check_registry():
    """负责 check_registry 的函数职责。"""
    response = request("GET", "/agent/tools")
    data = expect_ok_json(response, "GET /agent/tools")
    names = {tool.get("name") for tool in data.get("tools") or []}
    if "mcp.sqlite.query" not in names:
        fail_step("unified registry missing mcp.sqlite.query", response)
    if "sqlite_readonly_query" not in names:
        fail_step("local sqlite_readonly_query missing", response)

    pass_step("Unified registry includes SQLite MCP and local SQLite tool")


def check_list_tables_and_query():
    """负责 check_list_tables_and_query 的函数职责。"""
    response = request(
        "POST",
        "/agent/mcp/tools/mcp.sqlite.list-tables/run",
        json={"arguments": {}},
    )
    data = expect_ok_json(response, "POST /agent/mcp/tools/mcp.sqlite.list-tables/run")
    if not data.get("ok"):
        fail_step("mcp.sqlite.list-tables returned ok=false", response)
    assert_sqlite_metadata(data, response, "list-tables")
    if "conversation" not in ((data.get("result") or {}).get("text") or ""):
        fail_step("mcp.sqlite.list-tables missing conversation table", response)
    pass_step("SQLite MCP table list")

    response = request(
        "POST",
        "/agent/mcp/tools/mcp.sqlite.query/run",
        json={
            "arguments": {
                "sql": "SELECT COUNT(*) AS count FROM conversation",
            }
        },
    )
    data = expect_ok_json(response, "POST /agent/mcp/tools/mcp.sqlite.query/run")
    if not data.get("ok"):
        fail_step("mcp.sqlite.query returned ok=false", response)
    assert_sqlite_metadata(data, response, "query")
    if "count" not in ((data.get("result") or {}).get("text") or ""):
        fail_step("mcp.sqlite.query missing count result", response)
    pass_step("SQLite MCP SELECT")

    response = request(
        "POST",
        "/agent/mcp/tools/mcp.sqlite.describe-table/run",
        json={
            "arguments": {
                "tableName": "conversation",
            }
        },
    )
    data = expect_ok_json(response, "POST /agent/mcp/tools/mcp.sqlite.describe-table/run")
    if not data.get("ok"):
        fail_step("mcp.sqlite.describe-table returned ok=false", response)
    assert_sqlite_metadata(data, response, "describe-table")
    if "updated_time" not in ((data.get("result") or {}).get("text") or ""):
        fail_step("mcp.sqlite.describe-table missing schema detail", response)
    pass_step("SQLite MCP describe table")


def check_sql_rejections():
    """负责 check_sql_rejections 的函数职责。"""
    cases = [
        ("UPDATE", "UPDATE conversation SET title = title"),
        ("DELETE", "DELETE FROM conversation WHERE 1=0"),
        ("DROP", "DROP TABLE conversation"),
        ("ATTACH", "ATTACH DATABASE 'other.db' AS other"),
    ]
    for label, sql in cases:
        response = request(
            "POST",
            "/agent/mcp/tools/mcp.sqlite.query/run",
            json={
                "arguments": {
                    "sql": sql,
                }
            },
        )
        data = expect_ok_json(response, f"SQLite MCP rejects {label}")
        if data.get("ok"):
            fail_step(f"{label} should be rejected", response)
        error = data.get("error") or ""
        if "allowed" not in error:
            fail_step(f"{label} rejection message unclear", response)

    pass_step("SQLite MCP write SQL rejections")


def check_unknown_tool_rejected():
    """负责 check_unknown_tool_rejected 的函数职责。"""
    response = request(
        "POST",
        "/agent/mcp/tools/mcp.sqlite.execute/run",
        json={
            "arguments": {
                "sql": "UPDATE conversation SET title = title",
            }
        },
    )
    data = expect_ok_json(response, "SQLite MCP unknown/write tool rejected")
    if data.get("ok"):
        fail_step("mcp.sqlite.execute should not be registered", response)
    if "not allowed" not in (data.get("error") or ""):
        fail_step("unknown/write tool rejection missing allowlist message", response)

    pass_step("SQLite MCP unknown tool rejection")


def check_planner_sqlite_mcp():
    """负责 check_planner_sqlite_mcp 的函数职责。"""
    response = request(
        "POST",
        "/agent/plan_run",
        json={
            "query": (
                "Use mcp.sqlite.query to run this exact SQL: "
                "SELECT COUNT(*) AS count FROM conversation"
            ),
            "kb_name": "default",
            "tools": ["mcp.sqlite.query"],
            "max_steps": 3,
        },
    )
    data = expect_ok_json(response, "POST /agent/plan_run SQLite MCP")
    if data.get("error"):
        fail_step("planner SQLite MCP run returned error", response)

    steps = data.get("steps") or []
    if not steps or steps[0].get("tool_call", {}).get("tool") != "mcp.sqlite.query":
        fail_step("planner did not call mcp.sqlite.query", response)

    tool_result = steps[0].get("tool_result") or {}
    if not tool_result.get("ok"):
        fail_step("planner SQLite MCP tool_result ok=false", response)

    trace = data.get("trace") or []
    if not any(
        item.get("provider") == "mcp"
        and item.get("server") == "sqlite"
        and item.get("tool") == "query"
        for item in trace
    ):
        fail_step("planner trace missing SQLite MCP provider metadata", response)

    conversation_id = data.get("conversation_id")
    assistant_message_id = data.get("assistant_message_id")
    message_response = request("GET", f"/conversations/{conversation_id}/messages")
    message_data = expect_ok_json(
        message_response,
        f"GET /conversations/{conversation_id}/messages",
    )
    message = next(
        (
            item
            for item in message_data.get("messages", [])
            if item.get("id") == assistant_message_id
        ),
        None,
    )
    if message is None:
        fail_step("planner SQLite MCP assistant message missing", message_response)

    metadata = message.get("metadata") or {}
    if metadata.get("version") != "agent-v3":
        fail_step("planner metadata version mismatch", message_response)
    if not any(
        item.get("provider") == "mcp"
        and item.get("server") == "sqlite"
        for item in metadata.get("trace") or []
    ):
        fail_step("persisted trace missing SQLite MCP metadata", message_response)

    print(
        "planner sqlite MCP summary="
        f"conversation_id={conversation_id}, assistant_message_id={assistant_message_id}"
    )
    pass_step("Planner can call SQLite MCP and persist trace")


def check_local_sqlite_unaffected():
    """负责 check_local_sqlite_unaffected 的函数职责。"""
    response = request(
        "POST",
        "/agent/tools/sqlite_readonly_query/run",
        json={
            "arguments": {
                "sql": "SELECT COUNT(*) AS count FROM conversation",
            }
        },
    )
    data = expect_ok_json(response, "POST /agent/tools/sqlite_readonly_query/run")
    if not data.get("ok"):
        fail_step("local sqlite_readonly_query returned ok=false", response)
    if "count" not in str(data.get("result")):
        fail_step("local sqlite_readonly_query missing count", response)

    pass_step("Local sqlite_readonly_query unaffected")


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    check_sqlite_discovery()
    check_registry()
    check_list_tables_and_query()
    check_sql_rejections()
    check_unknown_tool_rejected()
    check_planner_sqlite_mcp()
    check_local_sqlite_unaffected()
    pass_step("SQLite MCP readonly smoke test complete")


if __name__ == "__main__":
    main()
