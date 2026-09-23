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
        print(f"body={response.text[:2200]}")

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


def run_planner_agent():
    """负责 run_planner_agent 的函数职责。"""
    response = request(
        "POST",
        "/agent/plan_run",
        json={
            "query": "Read README.md and summarize this project.",
            "kb_name": "default",
            "tools": ["filesystem_readonly_read"],
            "max_steps": 3,
        },
    )
    data = expect_ok_json(response, "POST /agent/plan_run")

    if data.get("error"):
        fail_step("planner agent returned unexpected error", response)

    if not data.get("answer"):
        fail_step("planner response missing final answer", response)

    if not data.get("conversation_id"):
        fail_step("planner response missing conversation_id", response)

    if not data.get("assistant_message_id"):
        fail_step("planner response missing assistant_message_id", response)

    planner = data.get("planner")
    if not isinstance(planner, dict):
        fail_step("planner response missing planner object", response)

    if not planner.get("goal"):
        fail_step("planner goal missing", response)

    steps = planner.get("steps")
    if not isinstance(steps, list) or len(steps) < 1:
        fail_step("planner steps missing", response)

    if planner.get("current_step") is None:
        fail_step("planner current_step missing", response)

    if planner.get("status") != "completed":
        fail_step("planner status should be completed", response)

    if not isinstance(data.get("trace"), list) or not data.get("trace"):
        fail_step("planner trace missing", response)

    print(
        "planner summary="
        f"conversation_id={data.get('conversation_id')}, "
        f"assistant_message_id={data.get('assistant_message_id')}, "
        f"goal={planner.get('goal')!r}, steps={len(steps)}, "
        f"current_step={planner.get('current_step')}"
    )
    pass_step("POST /agent/plan_run")
    return data


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
        fail_step("planner assistant message missing", response)

    return message, response


def assert_planner_metadata(message, expected_run, response, label):
    """负责 assert_planner_metadata 的函数职责。"""
    metadata = message.get("metadata")
    if not isinstance(metadata, dict):
        fail_step(f"{label}: metadata missing or not an object", response)

    required_keys = {
        "agent",
        "mode",
        "planner",
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

    if metadata.get("mode") != "planner":
        fail_step(f"{label}: metadata.mode is not planner", response)

    if metadata.get("version") != "agent-v3":
        fail_step(f"{label}: metadata.version is not agent-v3", response)

    planner = metadata.get("planner")
    if not isinstance(planner, dict):
        fail_step(f"{label}: metadata.planner missing", response)

    if not planner.get("goal"):
        fail_step(f"{label}: metadata planner goal missing", response)

    if not isinstance(planner.get("steps"), list) or len(planner["steps"]) < 1:
        fail_step(f"{label}: metadata planner steps missing", response)

    if planner.get("current_step") != expected_run.get("planner", {}).get("current_step"):
        fail_step(f"{label}: metadata planner current_step mismatch", response)

    if metadata.get("planner") != expected_run.get("planner"):
        fail_step(f"{label}: persisted planner differs from response", response)

    if metadata.get("trace") != expected_run.get("trace"):
        fail_step(f"{label}: persisted trace differs from response", response)

    print(
        f"{label} metadata summary="
        f"version={metadata.get('version')}, "
        f"planner_status={planner.get('status')}, "
        f"steps={len(planner.get('steps') or [])}"
    )
    pass_step(f"{label}: planner metadata persisted")


def check_agent_v2_compatibility():
    """负责 check_agent_v2_compatibility 的函数职责。"""
    response = request(
        "POST",
        "/agent/run_multi",
        json={
            "query": "25 * 8",
            "kb_name": "default",
            "tools": ["calculator"],
            "max_steps": 3,
        },
    )
    data = expect_ok_json(response, "POST /agent/run_multi compatibility")
    message, message_response = get_assistant_message(
        data.get("conversation_id"),
        data.get("assistant_message_id"),
    )
    metadata = message.get("metadata") or {}

    if metadata.get("version") != "agent-v2":
        fail_step("agent-v2 compatibility metadata version mismatch", message_response)

    if "planner" in metadata:
        fail_step("agent-v2 metadata should not require planner", message_response)

    pass_step("agent-v2 metadata remains compatible")


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    run_data = run_planner_agent()
    conversation_id = run_data["conversation_id"]
    assistant_message_id = run_data["assistant_message_id"]

    first_message, first_response = get_assistant_message(
        conversation_id,
        assistant_message_id,
    )
    assert_planner_metadata(
        first_message,
        run_data,
        first_response,
        "first read",
    )

    second_message, second_response = get_assistant_message(
        conversation_id,
        assistant_message_id,
    )
    assert_planner_metadata(
        second_message,
        run_data,
        second_response,
        "refresh read",
    )

    if json.dumps(first_message.get("metadata"), sort_keys=True) != json.dumps(
        second_message.get("metadata"),
        sort_keys=True,
    ):
        fail_step("planner metadata changed between repeated reads", second_response)

    check_agent_v2_compatibility()
    pass_step("Agent planner smoke test complete")


if __name__ == "__main__":
    main()
