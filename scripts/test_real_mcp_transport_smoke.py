import os
import sys
from pathlib import Path

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
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
    print(f"[PASS] {message}")


def fail_step(message, response=None):
    print(f"[FAIL] {message}")

    if response is not None:
        print(f"status={response.status_code}")
        print(f"body={response.text[:2400]}")

    sys.exit(1)


def request(method, path, **kwargs):
    try:
        return requests.request(
            method,
            f"{API_BASE}{path}",
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
    lower = response.text.lower()
    for text in FORBIDDEN_TEXT:
        if text.lower() in lower:
            fail_step(f"{step_name}: forbidden text found: {text}", response)


def expect_ok_json(response, step_name):
    assert_safe_response(response, step_name)

    if response.status_code != 200:
        fail_step(f"{step_name}: HTTP status is not 200", response)

    try:
        return response.json()
    except ValueError:
        fail_step(f"{step_name}: response is not JSON", response)


def assert_no_public_leaks(value, step_name):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in BLOCKED_PUBLIC_KEYS:
                fail_step(f"{step_name}: leaked {key}")
            assert_no_public_leaks(child, step_name)
    elif isinstance(value, list):
        for child in value:
            assert_no_public_leaks(child, step_name)


def check_filesystem_stdio_process_starts():
    response = request("GET", "/agent/mcp/tools")
    data = expect_ok_json(response, "GET /agent/mcp/tools")
    assert_no_public_leaks(data, "GET /agent/mcp/tools")

    tools = data.get("tools") or []
    stdio_tools = [
        tool
        for tool in tools
        if tool.get("server_name") == "filesystem_stdio"
    ]
    if not stdio_tools:
        fail_step("filesystem_stdio tools missing from real MCP discovery", response)

    names = {tool.get("tool_name") for tool in stdio_tools}
    if "read_file" not in names and "list_allowed_directories" not in names:
        fail_step("real MCP discovery did not expose an expected read-only tool", response)

    for tool in stdio_tools:
        if tool.get("qualified_name") != f"mcp.filesystem_stdio.{tool.get('tool_name')}":
            fail_step("filesystem_stdio tool name was not normalized from discovery", response)
        if tool.get("read_only") is not True or tool.get("risk_level") != "low":
            fail_step("filesystem_stdio tool safety metadata invalid", response)
        lowered = (tool.get("tool_name") or "").lower()
        if any(marker in lowered for marker in ("write", "edit", "delete", "remove", "create")):
            fail_step("write-like filesystem_stdio tool was registered", response)

    print(f"real discovery summary={sorted(names)}")
    pass_step("filesystem MCP process initialize and tools/list")
    return names


def check_server_status_initialized():
    response = request("GET", "/agent/mcp/servers")
    data = expect_ok_json(response, "GET /agent/mcp/servers")
    assert_no_public_leaks(data, "GET /agent/mcp/servers")

    servers = data.get("servers") or []
    server = next((item for item in servers if item.get("server") == "filesystem_stdio"), None)
    if not server:
        fail_step("filesystem_stdio server missing", response)

    if server.get("transport") != "stdio":
        fail_step("filesystem_stdio transport metadata missing", response)
    if server.get("running") is not True or server.get("initialized") is not True:
        fail_step("filesystem_stdio server did not report initialized process", response)

    pass_step("filesystem MCP health/status")


def check_real_tool_call(discovered_names):
    if "read_file" in discovered_names:
        tool = "mcp.filesystem_stdio.read_file"
        arguments = {
            "path": str(ROOT_DIR / "README.md"),
        }
    else:
        tool = "mcp.filesystem_stdio.list_allowed_directories"
        arguments = {}

    response = request(
        "POST",
        f"/agent/mcp/tools/{tool}/run",
        json={
            "arguments": arguments,
        },
    )
    data = expect_ok_json(response, f"POST /agent/mcp/tools/{tool}/run")
    assert_no_public_leaks(data, f"POST /agent/mcp/tools/{tool}/run")

    if not data.get("ok"):
        fail_step("filesystem_stdio tools/call returned ok=false", response)

    metadata = data.get("metadata") or {}
    if metadata.get("server") != "filesystem_stdio":
        fail_step("filesystem_stdio tools/call metadata server mismatch", response)
    if metadata.get("provider") != "mcp" or metadata.get("transport") != "stdio":
        fail_step("filesystem_stdio tools/call metadata transport mismatch", response)
    if metadata.get("read_only") is not True or metadata.get("risk_level") != "low":
        fail_step("filesystem_stdio tools/call safety metadata mismatch", response)

    result = data.get("result") or {}
    text = result.get("text") or ""
    if tool.endswith(".read_file") and "Mini ChatChat" not in text:
        fail_step("filesystem_stdio read_file did not return README content", response)

    print(f"real tools/call summary=tool={tool}, text_chars={len(text)}")
    pass_step("filesystem MCP real tools/call")


def check_rejections_and_timeout_shape():
    unknown = request(
        "POST",
        "/agent/mcp/tools/mcp.missing.read_file/run",
        json={"arguments": {}},
    )
    data = expect_ok_json(unknown, "unknown MCP server rejection")
    if data.get("ok") is not False or "not allowed" not in (data.get("error") or ""):
        fail_step("unknown server was not rejected with structured error", unknown)

    timeout_like = request(
        "POST",
        "/agent/mcp/tools/mcp.filesystem_stdio.unknown_tool/run",
        json={"arguments": {}},
    )
    data = expect_ok_json(timeout_like, "unknown MCP tool rejection")
    if data.get("ok") is not False or not isinstance(data.get("metadata"), dict):
        fail_step("unknown tool did not return structured error", timeout_like)

    pass_step("structured MCP errors")


def check_bad_command_rejected():
    sys.path.insert(0, str(ROOT_DIR / "backend"))
    from services.mcp_transport import StdioMCPServer, StdioMCPServerConfig

    server = StdioMCPServer(
        StdioMCPServerConfig(
            server_name="bad",
            command="/bin/sh",
            args=["-c", "echo unsafe"],
            cwd=str(ROOT_DIR),
            env_allowlist=[],
            startup_timeout=0.1,
            call_timeout=0.1,
        )
    )

    try:
        server.list_tools()
    except ValueError:
        pass_step("non-allowlist command rejected")
        return

    fail_step("non-allowlist command was not rejected")


def check_shutdown_cleanup():
    response = request("POST", "/agent/mcp/servers/filesystem_stdio/shutdown")
    data = expect_ok_json(response, "POST /agent/mcp/servers/filesystem_stdio/shutdown")
    assert_no_public_leaks(data, "POST /agent/mcp/servers/filesystem_stdio/shutdown")

    server = data.get("server") or {}
    if server.get("running") is not False or server.get("initialized") is not False:
        fail_step("filesystem_stdio process did not shut down cleanly", response)

    pass_step("filesystem MCP shutdown cleanup")


def main():
    print(f"API_BASE={API_BASE}")
    names = check_filesystem_stdio_process_starts()
    check_server_status_initialized()
    check_real_tool_call(names)
    check_rejections_and_timeout_shape()
    check_bad_command_rejected()
    check_shutdown_cleanup()
    pass_step("Real MCP stdio transport smoke test complete")


if __name__ == "__main__":
    main()
