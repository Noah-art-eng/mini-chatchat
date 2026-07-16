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

    names = {
        tool.get("name")
        for tool in data.get("tools", [])
    }

    if "browser_search" not in names:
        fail_step("browser_search missing from tool registry", response)

    print(f"tools summary={sorted(names)}")
    pass_step("GET /agent/tools includes browser_search")


def check_direct_browser_search():
    response = request(
        "POST",
        "/agent/tools/browser_search/run",
        json={
            "arguments": {
                "query": "OpenAI latest news",
                "max_results": 2,
            }
        },
    )
    data = expect_ok_json(response, "POST /agent/tools/browser_search/run")

    if not data.get("ok"):
        fail_step("browser_search returned ok=false", response)

    result = data.get("result") or {}
    results = result.get("results") or []

    if len(results) > 2:
        fail_step("browser_search exceeded max_results", response)

    if results:
        first = results[0]
        if not all(key in first for key in ["title", "url", "snippet"]):
            fail_step("browser_search missing title/url/snippet", response)

    print(
        "browser_search summary="
        f"result_count={result.get('result_count')}, first_url={(results[0] or {}).get('url') if results else ''}"
    )
    pass_step("POST /agent/tools/browser_search/run")


def check_agent_run_browser_search():
    response = request(
        "POST",
        "/agent/run",
        json={
            "query": "Search the web for latest OpenAI news",
            "kb_name": "default",
            "tools": ["browser_search"],
        },
    )
    data = expect_ok_json(response, "POST /agent/run browser_search")

    if data.get("error"):
        fail_step("agent browser_search returned unexpected error", response)

    tool_call = data.get("tool_call") or {}
    tool_result = data.get("tool_result") or {}

    if tool_call.get("tool") != "browser_search":
        fail_step("agent did not choose browser_search", response)

    if not tool_result.get("ok"):
        fail_step("agent browser_search tool_result ok=false", response)

    result = tool_result.get("result") or {}
    results = result.get("results") or []
    if results and not all(key in results[0] for key in ["title", "url", "snippet"]):
        fail_step("agent browser_search missing result fields", response)

    answer = data.get("answer") or ""
    if not answer.strip():
        fail_step("agent browser_search final answer missing", response)

    print(
        "agent browser_search summary="
        f"tool={tool_call.get('tool')}, results={len(results)}, answer={answer[:120]!r}"
    )
    pass_step("POST /agent/run browser_search")


def main():
    print(f"API_BASE={API_BASE}")
    check_tool_is_listed()
    check_direct_browser_search()
    check_agent_run_browser_search()
    pass_step("Browser search tool smoke test complete")


if __name__ == "__main__":
    main()
