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
        print(f"body={response.text[:1200]}")

    sys.exit(1)


def request(method, path, **kwargs):
    try:
        return requests.request(
            method,
            f"{API_BASE}{path}",
            timeout=90,
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


def run_tool(tool_name, arguments, step_name):
    response = request(
        "POST",
        f"/agent/tools/{tool_name}/run",
        json={"arguments": arguments},
    )
    return expect_ok_json(response, step_name), response


def check_tool_list():
    response = request("GET", "/agent/tools")
    data = expect_ok_json(response, "GET /agent/tools")
    tools = data.get("tools", [])
    names = {tool.get("name") for tool in tools}

    expected = {"current_time", "calculator", "kb_search"}
    if not expected.issubset(names):
        fail_step(f"GET /agent/tools: missing tools {expected - names}", response)

    if any("executor" in tool for tool in tools):
        fail_step("GET /agent/tools: executor leaked", response)

    print(f"tools summary={sorted(names)}")
    pass_step("GET /agent/tools")


def check_current_time():
    data, response = run_tool(
        "current_time",
        {},
        "POST /agent/tools/current_time/run",
    )

    if not data.get("ok"):
        fail_step("current_time returned ok=false", response)

    result = data.get("result", {})
    if not result.get("utc") or not result.get("local"):
        fail_step("current_time missing utc/local", response)

    print(f"current_time summary=utc={result.get('utc')}")
    pass_step("POST /agent/tools/current_time/run")


def check_calculator_success():
    data, response = run_tool(
        "calculator",
        {"expression": "25 * 8 + (10 % 3)"},
        "POST /agent/tools/calculator/run success",
    )

    if not data.get("ok"):
        fail_step("calculator success returned ok=false", response)

    value = data.get("result", {}).get("value")
    if value != 201:
        fail_step(f"calculator returned {value}, expected 201", response)

    print(f"calculator success summary=value={value}")
    pass_step("POST /agent/tools/calculator/run success")


def check_calculator_rejects_unsafe_expression():
    data, response = run_tool(
        "calculator",
        {"expression": "__import__('os').system('echo unsafe')"},
        "POST /agent/tools/calculator/run unsafe",
    )

    if data.get("ok"):
        fail_step("calculator accepted unsafe expression", response)

    if not data.get("error"):
        fail_step("calculator unsafe response missing error", response)

    print(f"calculator unsafe summary=error={data.get('error')!r}")
    pass_step("POST /agent/tools/calculator/run unsafe")


def check_kb_search():
    data, response = run_tool(
        "kb_search",
        {
            "query": "Docker",
            "kb_name": "default",
            "top_k": 3,
        },
        "POST /agent/tools/kb_search/run",
    )

    if not data.get("ok"):
        fail_step("kb_search returned ok=false", response)

    result = data.get("result", {})
    sources = result.get("sources", [])
    if not sources:
        fail_step("kb_search missing sources", response)

    first = sources[0]
    for key in ("source", "chunk", "hybrid_score", "bm25_score"):
        if key not in first:
            fail_step(f"kb_search missing source field: {key}", response)

    print(
        "kb_search summary="
        f"sources={len(sources)}, first_source={first.get('source')}, "
        f"hybrid_score={first.get('hybrid_score')}"
    )
    pass_step("POST /agent/tools/kb_search/run")


def main():
    print(f"API_BASE={API_BASE}")
    check_tool_list()
    check_current_time()
    check_calculator_success()
    check_calculator_rejects_unsafe_expression()
    check_kb_search()
    pass_step("Tool registry smoke test complete")


if __name__ == "__main__":
    main()
