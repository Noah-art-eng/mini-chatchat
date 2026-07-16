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


def assert_trace(data, step_name, response):
    trace = data.get("trace")
    if not isinstance(trace, list) or not trace:
        fail_step(f"{step_name}: trace missing", response)


def check_agent_calculator():
    response = request(
        "POST",
        "/agent/run",
        json={
            "query": "25 * 8",
            "kb_name": "default",
            "tools": ["calculator"],
        },
    )
    data = expect_ok_json(response, "POST /agent/run calculator")
    assert_trace(data, "POST /agent/run calculator", response)

    if data.get("error"):
        fail_step("POST /agent/run calculator: unexpected error", response)

    tool_call = data.get("tool_call") or {}
    tool_result = data.get("tool_result") or {}
    answer = data.get("answer") or ""

    if tool_call.get("tool") != "calculator":
        fail_step("agent calculator did not choose calculator", response)

    if not tool_result.get("ok"):
        fail_step("agent calculator tool_result ok=false", response)

    value = (tool_result.get("result") or {}).get("value")
    if value != 200:
        fail_step(f"agent calculator value={value}, expected 200", response)

    if not answer.strip() or "200" not in answer:
        fail_step("agent calculator final answer missing 200", response)

    print(f"agent calculator summary=answer={answer[:120]!r}")
    pass_step("POST /agent/run calculator")


def check_agent_kb_search():
    response = request(
        "POST",
        "/agent/run",
        json={
            "query": "Docker",
            "kb_name": "default",
            "tools": ["kb_search"],
        },
    )
    data = expect_ok_json(response, "POST /agent/run kb_search")
    assert_trace(data, "POST /agent/run kb_search", response)

    if data.get("error"):
        fail_step("POST /agent/run kb_search: unexpected error", response)

    tool_call = data.get("tool_call") or {}
    tool_result = data.get("tool_result") or {}
    answer = data.get("answer") or ""

    if tool_call.get("tool") != "kb_search":
        fail_step("agent kb_search did not choose kb_search", response)

    if not tool_result.get("ok"):
        fail_step("agent kb_search tool_result ok=false", response)

    sources = (tool_result.get("result") or {}).get("sources", [])
    if not sources:
        fail_step("agent kb_search missing sources", response)

    if not answer.strip():
        fail_step("agent kb_search final answer missing", response)

    print(
        "agent kb_search summary="
        f"answer={answer[:120]!r}, sources={len(sources)}"
    )
    pass_step("POST /agent/run kb_search")


def check_agent_none():
    response = request(
        "POST",
        "/agent/run",
        json={
            "query": "Say hello in one short sentence.",
            "kb_name": "default",
            "tools": [],
        },
    )
    data = expect_ok_json(response, "POST /agent/run none")
    assert_trace(data, "POST /agent/run none", response)

    if data.get("error"):
        fail_step("POST /agent/run none: unexpected error", response)

    tool_call = data.get("tool_call") or {}
    answer = data.get("answer") or ""

    if tool_call.get("tool") != "none":
        fail_step("agent none did not choose none", response)

    if data.get("tool_result") is not None:
        fail_step("agent none should not execute a tool", response)

    if not answer.strip():
        fail_step("agent none final answer missing", response)

    print(f"agent none summary=answer={answer[:120]!r}")
    pass_step("POST /agent/run none")


def main():
    print(f"API_BASE={API_BASE}")
    check_agent_calculator()
    check_agent_kb_search()
    check_agent_none()
    pass_step("Agent loop smoke test complete")


if __name__ == "__main__":
    main()
