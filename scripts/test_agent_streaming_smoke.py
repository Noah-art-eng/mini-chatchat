import json
import os
import sys

import requests

from smoke_auth import auth_headers


API_BASE = os.getenv(
    "MINI_CHATCHAT_API_BASE",
    "http://127.0.0.1:8000",
).rstrip("/")

FORBIDDEN = [
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "api_key",
    "command",
    "environment",
    "stderr",
]


def fail_step(message, response=None):
    """负责 fail_step 的函数职责。"""
    print(f"[FAIL] {message}")
    if response is not None:
        print(f"status={response.status_code}")
        print(f"body={response.text[:1200]}")
    sys.exit(1)


def pass_step(message):
    """负责 pass_step 的函数职责。"""
    print(f"[PASS] {message}")


def request(method, path, **kwargs):
    """负责 request 的函数职责。"""
    headers = kwargs.pop("headers", {})
    headers = {**auth_headers(), **headers}
    return requests.request(
        method,
        f"{API_BASE}{path}",
        headers=headers,
        timeout=90,
        **kwargs,
    )


def expect_ok_json(response, label):
    """负责 expect_ok_json 的函数职责。"""
    if response.status_code != 200:
        fail_step(f"{label} returned HTTP {response.status_code}", response)

    try:
        return response.json()
    except ValueError:
        fail_step(f"{label} did not return JSON", response)


def parse_sse_events(response):
    """负责 parse_sse_events 的函数职责。"""
    events = []
    raw_chunks = []
    current = []

    for line in response.iter_lines(decode_unicode=True):
        if line == "":
            if current:
                event_type = "message"
                data = ""
                for item in current:
                    if item.startswith("event:"):
                        event_type = item.replace("event:", "", 1).strip()
                    if item.startswith("data:"):
                        data = item.replace("data:", "", 1).strip()
                raw_chunks.append("\n".join(current))
                if data:
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError as exc:
                        fail_step(f"invalid SSE JSON event: {exc}")
                    if event.get("type") != event_type:
                        fail_step(f"SSE event type mismatch: {event_type} != {event.get('type')}")
                    events.append(event)
                current = []
            continue

        current.append(line)

    return events, "\n".join(raw_chunks)


def assert_no_leaks(text):
    """负责 assert_no_leaks 的函数职责。"""
    lowered = text.lower()
    for forbidden in FORBIDDEN:
        if forbidden.lower() in lowered:
            fail_step(f"stream leaked forbidden token: {forbidden}")


def assert_event_order(event_types):
    """负责 assert_event_order 的函数职责。"""
    required = [
        "planning",
        "step_start",
        "tool_call",
        "tool_result",
        "planner_update",
        "token",
        "done",
    ]
    positions = {}
    for item in required:
        try:
            positions[item] = event_types.index(item)
        except ValueError:
            fail_step(f"missing SSE event: {item}")

    ordered = [positions[item] for item in required]
    if ordered != sorted(ordered):
        fail_step(f"SSE events out of order: {event_types}")


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    health = request("GET", "/models")
    if health.status_code != 200:
        fail_step(f"Backend is not running at {API_BASE}", health)

    payload = {
        "query": "What is 25 * 8 and what is the current UTC time?",
        "kb_name": "default",
        "tools": ["calculator", "current_time"],
        "conversation_id": None,
        "max_steps": 3,
    }
    response = requests.post(
        f"{API_BASE}/agent/plan_run_stream",
        headers=auth_headers(),
        json=payload,
        stream=True,
        timeout=90,
    )

    content_type = response.headers.get("content-type", "")
    if response.status_code != 200:
        fail_step("/agent/plan_run_stream returned non-200", response)
    if "text/event-stream" not in content_type:
        fail_step(f"/agent/plan_run_stream content-type was {content_type}", response)

    events, raw_stream = parse_sse_events(response)
    assert_no_leaks(raw_stream)
    event_types = [event.get("type") for event in events]
    assert_event_order(event_types)
    if not any(event.get("type") == "token" and event.get("content") for event in events):
        fail_step("stream did not include a token payload")

    done_events = [event for event in events if event.get("type") == "done"]
    if len(done_events) != 1:
        fail_step(f"expected exactly one done event, got {len(done_events)}")

    result = done_events[0].get("result") or {}
    conversation_id = result.get("conversation_id")
    assistant_message_id = result.get("assistant_message_id")
    if not conversation_id or not assistant_message_id:
        fail_step("done result missing conversation_id or assistant_message_id")
    if result.get("error"):
        fail_step(f"done result returned error: {result.get('error')}")
    if "200" not in (result.get("answer") or ""):
        fail_step("final answer did not include arithmetic result 200")

    pass_step("SSE stream events and done result")

    messages_response = request("GET", f"/conversations/{conversation_id}/messages")
    messages_data = expect_ok_json(messages_response, "GET conversation messages")
    assistant_messages = [
        message
        for message in messages_data.get("messages", [])
        if message.get("id") == assistant_message_id
    ]
    if len(assistant_messages) != 1:
        fail_step("assistant message not persisted exactly once", messages_response)

    metadata = assistant_messages[0].get("metadata") or {}
    if not metadata.get("agent"):
        fail_step("assistant metadata missing agent=true", messages_response)
    if metadata.get("version") != "agent-v3":
        fail_step(f"assistant metadata version changed: {metadata.get('version')}")
    for key in ["planner", "steps", "trace", "tool_count"]:
        if key not in metadata:
            fail_step(f"assistant metadata missing {key}", messages_response)
    metadata_before = json.dumps(metadata, sort_keys=True)

    refresh_response = request("GET", f"/conversations/{conversation_id}/messages")
    refresh_data = expect_ok_json(refresh_response, "refresh conversation messages")
    refreshed = [
        message
        for message in refresh_data.get("messages", [])
        if message.get("id") == assistant_message_id
    ][0].get("metadata") or {}
    metadata_after = json.dumps(refreshed, sort_keys=True)
    if metadata_before != metadata_after:
        fail_step("metadata changed after refresh")

    pass_step("metadata persisted and refresh stable")

    plan_response = request(
        "POST",
        "/agent/plan_run",
        json={
            "query": "What is 25 * 8?",
            "kb_name": "default",
            "tools": ["calculator"],
            "conversation_id": None,
            "max_steps": 3,
        },
    )
    plan_data = expect_ok_json(plan_response, "POST /agent/plan_run")
    if plan_data.get("error"):
        fail_step("/agent/plan_run returned error", plan_response)
    if plan_data.get("conversation_id") == conversation_id:
        fail_step("/agent/plan_run reused streaming conversation unexpectedly")

    pass_step("original /agent/plan_run unaffected")
    pass_step("Agent streaming smoke test complete")


if __name__ == "__main__":
    main()
