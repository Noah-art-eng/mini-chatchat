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
    "environment",
)


def pass_step(message):
    """负责 pass_step 的函数职责。"""
    print(f"[PASS] {message}")


def fail_step(message, response=None):
    """负责 fail_step 的函数职责。"""
    print(f"[FAIL] {message}")

    if response is not None:
        print(f"status={response.status_code}")
        print(f"body={response.text[:1600]}")

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
            timeout=60,
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


def check_list_mcp_tools():
    """负责 check_list_mcp_tools 的函数职责。"""
    response = request("GET", "/agent/mcp/tools")
    data = expect_ok_json(response, "GET /agent/mcp/tools")

    tools = data.get("tools") or []
    names = {
        tool.get("qualified_name")
        for tool in tools
    }

    if "mcp.demo.echo" not in names:
        fail_step("GET /agent/mcp/tools missing mcp.demo.echo", response)

    print(f"mcp tools summary={sorted(names)}")
    pass_step("GET /agent/mcp/tools")


def check_demo_echo():
    """负责 check_demo_echo 的函数职责。"""
    response = request(
        "POST",
        "/agent/mcp/tools/mcp.demo.echo/run",
        json={
            "arguments": {
                "message": "hello mcp adapter",
            }
        },
    )
    data = expect_ok_json(response, "POST /agent/mcp/tools/mcp.demo.echo/run")

    if not data.get("ok"):
        fail_step("demo echo returned ok=false", response)

    result = data.get("result") or {}
    if result.get("message") != "hello mcp adapter":
        fail_step("demo echo returned wrong message", response)

    metadata = data.get("metadata") or {}
    if (
        metadata.get("server") != "demo"
        or metadata.get("provider") != "mcp"
        or metadata.get("read_only") is not True
    ):
        fail_step("demo echo metadata missing safety marker", response)

    print(f"demo echo summary=result={result}")
    pass_step("POST /agent/mcp/tools/mcp.demo.echo/run")


def check_reject_unknown_tool():
    """负责 check_reject_unknown_tool 的函数职责。"""
    response = request(
        "POST",
        "/agent/mcp/tools/mcp.filesystem.read_file/run",
        json={
            "arguments": {
                "path": "/etc/passwd",
            }
        },
    )
    data = expect_ok_json(
        response,
        "POST /agent/mcp/tools/mcp.filesystem.read_file/run",
    )

    if data.get("ok"):
        fail_step("unknown MCP tool should be rejected", response)

    error = data.get("error") or ""
    if "not allowed" not in error:
        fail_step("unknown MCP tool did not return allowlist error", response)

    print(f"unknown mcp tool summary=error={error!r}")
    pass_step("POST /agent/mcp/tools/mcp.filesystem.read_file/run rejected")


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    check_list_mcp_tools()
    check_demo_echo()
    check_reject_unknown_tool()
    pass_step("MCP adapter smoke test complete")


if __name__ == "__main__":
    main()
