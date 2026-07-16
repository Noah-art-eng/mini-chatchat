import json
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
    "MCP command",
    "environment",
)


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


def check_servers():
    response = request("GET", "/agent/mcp/servers")
    data = expect_ok_json(response, "GET /agent/mcp/servers")
    servers = data.get("servers") or []
    demo = next((item for item in servers if item.get("server") == "demo"), None)

    if not demo:
        fail_step("demo MCP server missing", response)

    if demo.get("tool_count", 0) < 1 or demo.get("enabled") is not True:
        fail_step("demo MCP server discovery metadata invalid", response)

    for forbidden_key in ("command", "cwd", "env"):
        if forbidden_key in demo:
            fail_step(f"server response leaked {forbidden_key}", response)

    print(f"mcp servers summary={servers}")
    pass_step("MCP server discovery")


def check_mcp_tools():
    response = request("GET", "/agent/mcp/tools")
    data = expect_ok_json(response, "GET /agent/mcp/tools")
    tools = data.get("tools") or []
    names = {tool.get("qualified_name") for tool in tools}

    if "mcp.demo.echo" not in names:
        fail_step("mcp.demo.echo missing from MCP tool discovery", response)

    echo = next(tool for tool in tools if tool.get("qualified_name") == "mcp.demo.echo")
    if echo.get("provider") != "mcp":
        fail_step("mcp.demo.echo provider mismatch", response)

    if echo.get("read_only") is not True or echo.get("risk_level") != "low":
        fail_step("mcp.demo.echo safety fields invalid", response)

    print(f"mcp tools summary={sorted(names)}")
    pass_step("MCP tool discovery")


def check_registry_sees_mcp_and_local():
    response = request("GET", "/agent/tools")
    data = expect_ok_json(response, "GET /agent/tools")
    tools = data.get("tools") or []
    names = {tool.get("name") for tool in tools}

    if "mcp.demo.echo" not in names:
        fail_step("unified registry missing mcp.demo.echo", response)

    if "calculator" not in names:
        fail_step("unified registry missing local calculator", response)

    print("unified registry summary=contains mcp.demo.echo and calculator")
    pass_step("Unified registry sees MCP and local tools")


def check_mcp_call():
    response = request(
        "POST",
        "/agent/mcp/tools/mcp.demo.echo/run",
        json={
            "arguments": {
                "message": "hello real mcp",
            }
        },
    )
    data = expect_ok_json(response, "POST /agent/mcp/tools/mcp.demo.echo/run")

    if not data.get("ok"):
        fail_step("mcp.demo.echo returned ok=false", response)

    if (data.get("result") or {}).get("message") != "hello real mcp":
        fail_step("mcp.demo.echo returned wrong message", response)

    metadata = data.get("metadata") or {}
    expected = {
        "provider": "mcp",
        "server": "demo",
        "tool": "echo",
        "read_only": True,
        "risk_level": "low",
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            fail_step(f"mcp.demo.echo metadata mismatch for {key}", response)

    print(f"mcp call summary=result={data.get('result')}, metadata={metadata}")
    pass_step("MCP tool call")


def check_rejections():
    cases = [
        ("unknown server", "/agent/mcp/tools/mcp.unknown.echo/run"),
        ("unknown tool", "/agent/mcp/tools/mcp.demo.unknown/run"),
        ("non allowlist", "/agent/mcp/tools/mcp.demo.write_file/run"),
    ]

    for label, path in cases:
        response = request(
            "POST",
            path,
            json={
                "arguments": {
                    "message": "blocked",
                }
            },
        )
        data = expect_ok_json(response, f"POST {path}")
        if data.get("ok"):
            fail_step(f"{label} should be rejected", response)

        error = data.get("error") or ""
        if "not allowed" not in error:
            fail_step(f"{label} rejection missing allowlist message", response)

    pass_step("MCP safety rejections")


def check_agent_plan_run_mcp():
    response = request(
        "POST",
        "/agent/plan_run",
        json={
            "query": "Use mcp.demo.echo to echo 'hello planner mcp'.",
            "kb_name": "default",
            "tools": ["mcp.demo.echo"],
            "max_steps": 3,
        },
    )
    data = expect_ok_json(response, "POST /agent/plan_run MCP")

    if data.get("error"):
        fail_step("planner MCP run returned unexpected error", response)

    trace = data.get("trace") or []
    provider_events = [
        item
        for item in trace
        if item.get("provider") == "mcp"
        and item.get("server") == "demo"
        and item.get("tool") == "echo"
    ]
    if not provider_events:
        fail_step("planner MCP trace missing provider metadata", response)

    steps = data.get("steps") or []
    if not steps or steps[0].get("tool_call", {}).get("tool") != "mcp.demo.echo":
        fail_step("planner MCP step did not call mcp.demo.echo", response)

    tool_result = steps[0].get("tool_result") or {}
    if not tool_result.get("ok"):
        fail_step("planner MCP tool result not ok", response)

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
        fail_step("planner MCP assistant message not found", message_response)

    metadata = message.get("metadata") or {}
    if metadata.get("agent") is not True or metadata.get("version") != "agent-v3":
        fail_step("planner MCP metadata version mismatch", message_response)

    metadata_trace = metadata.get("trace") or []
    if not any(item.get("provider") == "mcp" for item in metadata_trace):
        fail_step("persisted metadata trace missing MCP provider", message_response)

    print(
        "planner MCP summary="
        f"conversation_id={conversation_id}, "
        f"assistant_message_id={assistant_message_id}, "
        f"trace_events={len(trace)}"
    )
    pass_step("Planner can call MCP tool and persist metadata")


def check_local_tool_still_works():
    response = request(
        "POST",
        "/agent/tools/calculator/run",
        json={
            "arguments": {
                "expression": "25 * 8",
            }
        },
    )
    data = expect_ok_json(response, "POST /agent/tools/calculator/run")

    if not data.get("ok") or (data.get("result") or {}).get("value") != 200:
        fail_step("local calculator tool regression", response)

    pass_step("Local tool unaffected")


def main():
    print(f"API_BASE={API_BASE}")
    check_servers()
    check_mcp_tools()
    check_registry_sees_mcp_and_local()
    check_mcp_call()
    check_rejections()
    check_agent_plan_run_mcp()
    check_local_tool_still_works()
    pass_step("Real MCP integration foundation smoke test complete")


if __name__ == "__main__":
    main()
