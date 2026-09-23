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


def pass_step(message):
    """负责 pass_step 的函数职责。"""
    print(f"[PASS] {message}")


def fail_step(message, response=None):
    """负责 fail_step 的函数职责。"""
    print(f"[FAIL] {message}")

    if response is not None:
        print(f"status={response.status_code}")
        print(f"body={response.text[:2400]}")

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
            timeout=180,
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
    for text in FORBIDDEN_TEXT:
        if text.lower() in response.text.lower():
            fail_step(f"{step_name}: forbidden text found: {text}", response)


def expect_ok_json(response, step_name):
    """负责 expect_ok_json 的函数职责。"""
    assert_safe_response(response, step_name)

    if response.status_code != 200:
        fail_step(f"{step_name}: HTTP status is not 200", response)

    try:
        return response.json()
    except ValueError:
        fail_step(f"{step_name}: response is not JSON", response)


def assert_mcp_metadata(data, response, tool_name):
    """负责 assert_mcp_metadata 的函数职责。"""
    metadata = data.get("metadata") or {}
    expected = {
        "provider": "mcp",
        "server": "filesystem",
        "tool": tool_name,
        "read_only": True,
        "risk_level": "low",
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            fail_step(f"metadata mismatch for {key}", response)

    for blocked_key in ("command", "cmd", "cwd", "env", "stderr", "stdout"):
        if blocked_key in metadata:
            fail_step(f"metadata leaked {blocked_key}", response)


def check_discovery():
    """负责 check_discovery 的函数职责。"""
    response = request("GET", "/agent/mcp/servers")
    data = expect_ok_json(response, "GET /agent/mcp/servers")
    servers = data.get("servers") or []
    filesystem = next(
        (item for item in servers if item.get("server") == "filesystem"),
        None,
    )
    if not filesystem:
        fail_step("filesystem MCP server missing", response)

    if filesystem.get("enabled") is not True or filesystem.get("tool_count", 0) < 2:
        fail_step("filesystem MCP server metadata invalid", response)

    response = request("GET", "/agent/mcp/tools")
    data = expect_ok_json(response, "GET /agent/mcp/tools")
    tools = data.get("tools") or []
    names = {tool.get("qualified_name") for tool in tools}
    required = {
        "mcp.filesystem.read_file",
        "mcp.filesystem.list_dir",
    }
    missing = required - names
    if missing:
        fail_step(f"filesystem MCP tools missing {sorted(missing)}", response)

    for tool in tools:
        if tool.get("qualified_name") in required:
            if tool.get("provider") != "mcp":
                fail_step("filesystem MCP provider mismatch", response)
            if tool.get("read_only") is not True or tool.get("risk_level") != "low":
                fail_step("filesystem MCP safety fields invalid", response)

    print(f"filesystem MCP discovery summary={sorted(required)}")
    pass_step("Filesystem MCP discovery")


def check_registry():
    """负责 check_registry 的函数职责。"""
    response = request("GET", "/agent/tools")
    data = expect_ok_json(response, "GET /agent/tools")
    names = {tool.get("name") for tool in data.get("tools") or []}
    if "mcp.filesystem.read_file" not in names:
        fail_step("unified registry missing mcp.filesystem.read_file", response)

    if "filesystem_readonly_read" not in names:
        fail_step("local filesystem tool regression", response)

    pass_step("Unified registry includes filesystem MCP and local tool")


def check_read_file():
    """负责 check_read_file 的函数职责。"""
    response = request(
        "POST",
        "/agent/mcp/tools/mcp.filesystem.read_file/run",
        json={
            "arguments": {
                "path": "docs/ROADMAP.md",
            }
        },
    )
    data = expect_ok_json(
        response,
        "POST /agent/mcp/tools/mcp.filesystem.read_file/run",
    )

    if not data.get("ok"):
        fail_step("filesystem MCP read_file returned ok=false", response)

    result = data.get("result") or {}
    if result.get("path") != "docs/ROADMAP.md":
        fail_step("filesystem MCP read_file path mismatch", response)

    if "Roadmap" not in result.get("content", ""):
        fail_step("filesystem MCP read_file missing file content", response)

    assert_mcp_metadata(data, response, "read_file")
    print(
        "filesystem read_file summary="
        f"chars={result.get('char_count')}, truncated={result.get('truncated')}"
    )
    pass_step("Filesystem MCP read_file")


def check_list_dir():
    """负责 check_list_dir 的函数职责。"""
    response = request(
        "POST",
        "/agent/mcp/tools/mcp.filesystem.list_dir/run",
        json={
            "arguments": {
                "path": "docs",
            }
        },
    )
    data = expect_ok_json(
        response,
        "POST /agent/mcp/tools/mcp.filesystem.list_dir/run",
    )

    if not data.get("ok"):
        fail_step("filesystem MCP list_dir returned ok=false", response)

    result = data.get("result") or {}
    names = {entry.get("name") for entry in result.get("entries") or []}
    if "ROADMAP.md" not in names or "PROJECT_STATE.md" not in names:
        fail_step("filesystem MCP list_dir missing docs entries", response)

    assert_mcp_metadata(data, response, "list_dir")
    print(f"filesystem list_dir summary=entries={sorted(names)}")
    pass_step("Filesystem MCP list_dir")


def check_rejections():
    """负责 check_rejections 的函数职责。"""
    cases = [
        (
            "absolute path",
            "mcp.filesystem.read_file",
            {"path": "/etc/passwd"},
            "absolute paths are not allowed",
        ),
        (
            "parent traversal",
            "mcp.filesystem.read_file",
            {"path": "../README.md"},
            "parent directory traversal is not allowed",
        ),
        (
            "database file",
            "mcp.filesystem.read_file",
            {"path": "backend/mini.db"},
            "path is blocked by safety policy",
        ),
        (
            "env file",
            "mcp.filesystem.read_file",
            {"path": ".env"},
            "path is blocked by safety policy",
        ),
        (
            "write tool",
            "mcp.filesystem.write_file",
            {"path": "README.md", "content": "blocked"},
            "not allowed",
        ),
    ]

    for label, tool_name, arguments, expected_error in cases:
        response = request(
            "POST",
            f"/agent/mcp/tools/{tool_name}/run",
            json={
                "arguments": arguments,
            },
        )
        data = expect_ok_json(response, f"POST /agent/mcp/tools/{tool_name}/run")
        if data.get("ok"):
            fail_step(f"{label} should be rejected", response)

        error = data.get("error") or ""
        if expected_error not in error:
            fail_step(f"{label} rejection mismatch: {error!r}", response)

    pass_step("Filesystem MCP safety rejections")


def check_agent_plan_run():
    """负责 check_agent_plan_run 的函数职责。"""
    response = request(
        "POST",
        "/agent/plan_run",
        json={
            "query": "Read docs/ROADMAP.md and summarize this project roadmap.",
            "kb_name": "default",
            "tools": ["mcp.filesystem.read_file"],
            "max_steps": 3,
        },
    )
    data = expect_ok_json(response, "POST /agent/plan_run filesystem MCP")

    if data.get("error"):
        fail_step("planner filesystem MCP returned unexpected error", response)

    steps = data.get("steps") or []
    if not steps or steps[0].get("tool_call", {}).get("tool") != "mcp.filesystem.read_file":
        fail_step("planner did not call mcp.filesystem.read_file", response)

    trace = data.get("trace") or []
    if not any(
        item.get("provider") == "mcp"
        and item.get("server") == "filesystem"
        and item.get("tool") == "read_file"
        for item in trace
    ):
        fail_step("planner trace missing filesystem MCP provider metadata", response)

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
        fail_step("filesystem MCP assistant message missing", message_response)

    metadata = message.get("metadata") or {}
    if metadata.get("version") != "agent-v3" or metadata.get("agent") is not True:
        fail_step("filesystem MCP metadata version mismatch", message_response)

    if not any(item.get("server") == "filesystem" for item in metadata.get("trace") or []):
        fail_step("persisted metadata trace missing filesystem MCP", message_response)

    print(
        "planner filesystem MCP summary="
        f"conversation_id={conversation_id}, "
        f"assistant_message_id={assistant_message_id}"
    )
    pass_step("Planner can call filesystem MCP and persist metadata")


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    check_discovery()
    check_registry()
    check_read_file()
    check_list_dir()
    check_rejections()
    check_agent_plan_run()
    pass_step("Filesystem MCP readonly smoke test complete")


if __name__ == "__main__":
    main()
