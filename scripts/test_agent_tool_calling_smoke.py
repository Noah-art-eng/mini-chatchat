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


def check_decide_calculator():
    """负责 check_decide_calculator 的函数职责。"""
    response = request(
        "POST",
        "/agent/decide",
        json={
            "query": "25 * 8",
            "kb_name": "default",
            "tools": ["calculator"],
        },
    )
    data = expect_ok_json(response, "POST /agent/decide calculator")

    if data.get("error"):
        fail_step("POST /agent/decide calculator: unexpected error", response)

    tool_call = data.get("tool_call") or {}
    if tool_call.get("tool") != "calculator":
        fail_step(
            f"POST /agent/decide calculator: got {tool_call.get('tool')}",
            response,
        )

    if not isinstance(tool_call.get("arguments"), dict):
        fail_step("POST /agent/decide calculator: arguments missing", response)

    print(f"decide calculator summary=tool_call={tool_call}")
    pass_step("POST /agent/decide calculator")


def check_run_once_calculator():
    """负责 check_run_once_calculator 的函数职责。"""
    response = request(
        "POST",
        "/agent/run_once",
        json={
            "query": "25 * 8",
            "kb_name": "default",
            "tools": ["calculator"],
        },
    )
    data = expect_ok_json(response, "POST /agent/run_once calculator")

    if data.get("error"):
        fail_step("POST /agent/run_once calculator: unexpected error", response)

    tool_call = data.get("tool_call") or {}
    tool_result = data.get("tool_result") or {}

    if tool_call.get("tool") != "calculator":
        fail_step("run_once calculator did not choose calculator", response)

    if not tool_result.get("ok"):
        fail_step("run_once calculator tool_result ok=false", response)

    value = (tool_result.get("result") or {}).get("value")
    if value != 200:
        fail_step(f"run_once calculator value={value}, expected 200", response)

    print(f"run_once calculator summary=value={value}")
    pass_step("POST /agent/run_once calculator")


def check_run_once_kb_search():
    """负责 check_run_once_kb_search 的函数职责。"""
    response = request(
        "POST",
        "/agent/run_once",
        json={
            "query": "Docker",
            "kb_name": "default",
            "tools": ["kb_search"],
        },
    )
    data = expect_ok_json(response, "POST /agent/run_once kb_search")

    if data.get("error"):
        fail_step("POST /agent/run_once kb_search: unexpected error", response)

    tool_call = data.get("tool_call") or {}
    tool_result = data.get("tool_result") or {}

    if tool_call.get("tool") != "kb_search":
        fail_step("run_once kb_search did not choose kb_search", response)

    if not tool_result.get("ok"):
        fail_step("run_once kb_search tool_result ok=false", response)

    sources = (tool_result.get("result") or {}).get("sources", [])
    if not sources:
        fail_step("run_once kb_search missing sources", response)

    first = sources[0]
    if "hybrid_score" not in first or "bm25_score" not in first:
        fail_step("run_once kb_search missing hybrid fields", response)

    print(
        "run_once kb_search summary="
        f"sources={len(sources)}, first_source={first.get('source')}"
    )
    pass_step("POST /agent/run_once kb_search")


def check_invalid_tool_name():
    """负责 check_invalid_tool_name 的函数职责。"""
    response = request(
        "POST",
        "/agent/run_once",
        json={
            "query": "25 * 8",
            "kb_name": "default",
            "tools": ["not_a_real_tool"],
        },
    )
    data = expect_ok_json(response, "POST /agent/run_once invalid tool")

    if not data.get("error"):
        fail_step("invalid tool did not return structured error", response)

    if data.get("tool_result") is not None:
        fail_step("invalid tool should not execute a tool", response)

    print(f"invalid tool summary=error={data.get('error')!r}")
    pass_step("POST /agent/run_once invalid tool")


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    check_decide_calculator()
    check_run_once_calculator()
    check_run_once_kb_search()
    check_invalid_tool_name()
    pass_step("Agent tool calling smoke test complete")


if __name__ == "__main__":
    main()
