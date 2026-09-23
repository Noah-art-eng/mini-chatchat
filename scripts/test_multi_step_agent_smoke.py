import json
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
        print(f"body={response.text[:2000]}")

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


def run_multi_step_agent():
    """负责 run_multi_step_agent 的函数职责。"""
    response = request(
        "POST",
        "/agent/run_multi",
        json={
            "query": "What is 25 * 8 and what is the current UTC time?",
            "kb_name": "default",
            "tools": ["calculator", "current_time"],
            "max_steps": 3,
        },
    )
    data = expect_ok_json(response, "POST /agent/run_multi")

    if data.get("error"):
        fail_step("multi-step agent returned unexpected error", response)

    conversation_id = data.get("conversation_id")
    assistant_message_id = data.get("assistant_message_id")
    steps = data.get("steps") or []
    trace = data.get("trace") or []

    if not conversation_id:
        fail_step("multi-step response missing conversation_id", response)

    if not assistant_message_id:
        fail_step("multi-step response missing assistant_message_id", response)

    if len(steps) < 2:
        fail_step("multi-step response should contain at least 2 steps", response)

    tools = [
        (step.get("tool_call") or {}).get("tool")
        for step in steps
    ]
    if "calculator" not in tools:
        fail_step("multi-step response missing calculator step", response)

    if "current_time" not in tools:
        fail_step("multi-step response missing current_time step", response)

    calculator_step = next(
        step
        for step in steps
        if (step.get("tool_call") or {}).get("tool") == "calculator"
    )
    calculator_result = calculator_step.get("tool_result") or {}
    calculator_value = (calculator_result.get("result") or {}).get("value")

    if calculator_value != 200:
        fail_step("calculator step did not return 200", response)

    if data.get("tool_count") != len(steps):
        fail_step("tool_count should match executed steps", response)

    if not isinstance(trace, list) or not trace:
        fail_step("multi-step trace missing", response)

    if not data.get("answer"):
        fail_step("multi-step final answer missing", response)

    print(
        "multi-step summary="
        f"conversation_id={conversation_id}, "
        f"assistant_message_id={assistant_message_id}, "
        f"tools={tools}, tool_count={data.get('tool_count')}"
    )
    pass_step("POST /agent/run_multi")
    return data


def find_conversation(conversation_id):
    """负责 find_conversation 的函数职责。"""
    response = request("GET", "/conversations")
    data = expect_ok_json(response, "GET /conversations")
    conversations = data.get("conversations") or []

    match = next(
        (
            conversation
            for conversation in conversations
            if conversation.get("id") == conversation_id
        ),
        None,
    )

    if match is None:
        fail_step("multi-step conversation missing from list", response)

    pass_step("GET /conversations includes multi-step conversation")


def get_assistant_message(conversation_id, assistant_message_id):
    """负责 get_assistant_message 的函数职责。"""
    response = request("GET", f"/conversations/{conversation_id}/messages")
    data = expect_ok_json(
        response,
        f"GET /conversations/{conversation_id}/messages",
    )
    messages = data.get("messages") or []
    message = next(
        (
            item
            for item in messages
            if item.get("id") == assistant_message_id
        ),
        None,
    )

    if message is None:
        fail_step("multi-step assistant message missing", response)

    return message, response


def assert_multi_step_metadata(message, expected_run, response, label):
    """负责 assert_multi_step_metadata 的函数职责。"""
    metadata = message.get("metadata")
    if not isinstance(metadata, dict):
        fail_step(f"{label}: metadata missing or not an object", response)

    required_keys = {
        "agent",
        "mode",
        "steps",
        "trace",
        "tool_count",
        "version",
    }
    missing = required_keys - set(metadata)
    if missing:
        fail_step(f"{label}: metadata missing keys {sorted(missing)}", response)

    if metadata.get("agent") is not True:
        fail_step(f"{label}: metadata.agent is not true", response)

    if metadata.get("mode") != "multi-step":
        fail_step(f"{label}: metadata.mode is not multi-step", response)

    if metadata.get("version") != "agent-v2":
        fail_step(f"{label}: metadata.version is not agent-v2", response)

    if metadata.get("tool_count") != expected_run.get("tool_count"):
        fail_step(f"{label}: metadata.tool_count mismatch", response)

    if metadata.get("steps") != expected_run.get("steps"):
        fail_step(f"{label}: persisted steps differ from response", response)

    if metadata.get("trace") != expected_run.get("trace"):
        fail_step(f"{label}: persisted trace differs from response", response)

    print(
        f"{label} metadata summary="
        f"version={metadata.get('version')}, "
        f"steps={len(metadata.get('steps') or [])}, "
        f"tool_count={metadata.get('tool_count')}"
    )
    pass_step(f"{label}: multi-step metadata persisted")


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    run_data = run_multi_step_agent()
    conversation_id = run_data["conversation_id"]
    assistant_message_id = run_data["assistant_message_id"]

    find_conversation(conversation_id)

    first_message, first_response = get_assistant_message(
        conversation_id,
        assistant_message_id,
    )
    assert_multi_step_metadata(
        first_message,
        run_data,
        first_response,
        "first read",
    )

    second_message, second_response = get_assistant_message(
        conversation_id,
        assistant_message_id,
    )
    assert_multi_step_metadata(
        second_message,
        run_data,
        second_response,
        "refresh read",
    )

    if json.dumps(first_message.get("metadata"), sort_keys=True) != json.dumps(
        second_message.get("metadata"),
        sort_keys=True,
    ):
        fail_step("metadata changed between repeated reads", second_response)

    pass_step("Multi-step agent smoke test complete")


if __name__ == "__main__":
    main()
