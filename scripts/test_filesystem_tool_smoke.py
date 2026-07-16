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


def run_filesystem_tool(path):
    return request(
        "POST",
        "/agent/tools/filesystem_readonly_read/run",
        json={
            "arguments": {
                "path": path,
            }
        },
    )


def check_tool_is_listed():
    response = request("GET", "/agent/tools")
    data = expect_ok_json(response, "GET /agent/tools")

    names = {
        tool.get("name")
        for tool in data.get("tools", [])
    }

    if "filesystem_readonly_read" not in names:
        fail_step("filesystem_readonly_read missing from tool registry", response)

    print(f"tools summary={sorted(names)}")
    pass_step("GET /agent/tools includes filesystem_readonly_read")


def check_read_readme():
    response = run_filesystem_tool("README.md")
    data = expect_ok_json(response, "read README.md")

    if not data.get("ok"):
        fail_step("README.md read returned ok=false", response)

    result = data.get("result") or {}
    content = result.get("content") or ""
    if "Mini ChatChat" not in content:
        fail_step("README.md content did not include expected title", response)

    print(
        "README summary="
        f"chars={result.get('char_count')}, truncated={result.get('truncated')}"
    )
    pass_step("filesystem_readonly_read README.md")


def check_read_backend_app():
    response = run_filesystem_tool("backend/app.py")
    data = expect_ok_json(response, "read backend/app.py")

    if not data.get("ok"):
        fail_step("backend/app.py read returned ok=false", response)

    content = ((data.get("result") or {}).get("content")) or ""
    if "FastAPI" not in content:
        fail_step("backend/app.py content did not include FastAPI", response)

    print("backend/app.py summary=contains FastAPI")
    pass_step("filesystem_readonly_read backend/app.py")


def check_rejected_path(path, expected):
    response = run_filesystem_tool(path)
    data = expect_ok_json(response, f"reject path {path}")

    if data.get("ok"):
        fail_step(f"{path} should be rejected", response)

    error = data.get("error") or ""
    if expected.lower() not in error.lower():
        fail_step(f"{path} error did not include {expected!r}", response)

    print(f"reject summary=path={path!r}, error={error!r}")
    pass_step(f"filesystem_readonly_read rejects {path}")


def check_agent_run_filesystem():
    response = request(
        "POST",
        "/agent/run",
        json={
            "query": "Read README.md and summarize what project this is.",
            "kb_name": "default",
            "tools": ["filesystem_readonly_read"],
        },
    )
    data = expect_ok_json(response, "POST /agent/run filesystem_readonly_read")

    if data.get("error"):
        fail_step("agent filesystem returned unexpected error", response)

    tool_call = data.get("tool_call") or {}
    tool_result = data.get("tool_result") or {}

    if tool_call.get("tool") != "filesystem_readonly_read":
        fail_step("agent did not choose filesystem_readonly_read", response)

    if not tool_result.get("ok"):
        fail_step("agent filesystem tool_result ok=false", response)

    result = tool_result.get("result") or {}
    if result.get("path") != "README.md":
        fail_step("agent filesystem read wrong path", response)

    answer = data.get("answer") or ""
    if not answer.strip():
        fail_step("agent filesystem final answer missing", response)

    print(
        "agent filesystem summary="
        f"path={result.get('path')}, answer={answer[:120]!r}"
    )
    pass_step("POST /agent/run filesystem_readonly_read")


def main():
    print(f"API_BASE={API_BASE}")
    check_tool_is_listed()
    check_read_readme()
    check_read_backend_app()
    check_rejected_path("/etc/passwd", "absolute")
    check_rejected_path("../README.md", "parent")
    check_rejected_path("backend/mini.db", "extension")
    check_agent_run_filesystem()
    pass_step("Filesystem readonly tool smoke test complete")


if __name__ == "__main__":
    main()
