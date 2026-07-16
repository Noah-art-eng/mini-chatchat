import os
import sys
from datetime import datetime

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


def parse_json(response, step_name):
    try:
        return response.json()
    except ValueError:
        fail_step(f"{step_name}: response is not JSON", response)


def expect_ok_json(response, step_name):
    assert_safe_response(response, step_name)

    if response.status_code != 200:
        fail_step(f"{step_name}: HTTP status is not 200", response)

    data = parse_json(response, step_name)

    if isinstance(data, dict) and data.get("error"):
        fail_step(f"{step_name}: response contains error", response)

    return data


def check_models():
    response = request("GET", "/models")
    data = expect_ok_json(response, "GET /models")
    chat = data.get("chat", {})
    print(
        "GET /models summary="
        f"provider={chat.get('provider')}, "
        f"model={chat.get('default_model')}, "
        f"base_url={chat.get('base_url')}"
    )
    pass_step("GET /models")


def create_conversation_via_chat():
    payload = {
        "mode": "local_kb",
        "kb_name": "default",
        "query": "Docker是什么",
        "stream": False,
        "top_k": 3,
        "score_threshold": 0.8,
        "prompt_name": "default",
        "return_direct": False,
        "rerank": False,
        "rerank_top_n": 3,
    }
    response = request("POST", "/kb_chat", json=payload)
    data = expect_ok_json(response, "POST /kb_chat local_kb")

    conversation_id = data.get("conversation_id")
    assistant_message_id = data.get("assistant_message_id")
    answer = data.get("answer") or data.get("content") or ""

    if not conversation_id:
        fail_step("POST /kb_chat local_kb: missing conversation_id", response)

    if not assistant_message_id:
        fail_step("POST /kb_chat local_kb: missing assistant_message_id", response)

    if not answer:
        fail_step("POST /kb_chat local_kb: missing answer/content", response)

    print(
        "POST /kb_chat local_kb summary="
        f"conversation_id={conversation_id}, "
        f"assistant_message_id={assistant_message_id}, "
        f"answer={answer[:120]!r}"
    )
    pass_step("POST /kb_chat local_kb")
    return conversation_id, assistant_message_id


def find_conversation(conversations, conversation_id):
    return next(
        (
            conversation
            for conversation in conversations
            if conversation.get("id") == conversation_id
        ),
        None,
    )


def check_conversation_exists(conversation_id):
    response = request("GET", "/conversations")
    data = expect_ok_json(response, "GET /conversations")
    conversations = data.get("conversations", [])
    conversation = find_conversation(conversations, conversation_id)

    if conversation is None:
        fail_step("GET /conversations: created conversation not found", response)

    if not conversation.get("updated_time"):
        fail_step("GET /conversations: conversation missing updated_time", response)

    print(
        "GET /conversations summary="
        f"found_id={conversation_id}, "
        f"title={conversation.get('title')!r}, "
        f"updated_time={conversation.get('updated_time')}"
    )
    pass_step("GET /conversations created conversation exists")
    return conversation


def check_messages(conversation_id, assistant_message_id):
    response = request("GET", f"/conversations/{conversation_id}/messages")
    data = expect_ok_json(
        response,
        f"GET /conversations/{conversation_id}/messages",
    )
    messages = data.get("messages", [])
    assistant_message = next(
        (
            message
            for message in messages
            if message.get("id") == assistant_message_id
            and message.get("role") == "assistant"
        ),
        None,
    )

    if assistant_message is None:
        fail_step(
            "GET conversation messages: assistant message not found",
            response,
        )

    has_sources = isinstance(assistant_message.get("sources"), list)
    has_metadata = "metadata" in assistant_message

    if not has_sources and not has_metadata:
        fail_step(
            "GET conversation messages: assistant message missing metadata/sources",
            response,
        )

    print(
        "GET conversation messages summary="
        f"messages={len(messages)}, "
        f"assistant_id={assistant_message_id}, "
        f"has_metadata={has_metadata}, "
        f"sources={len(assistant_message.get('sources') or [])}"
    )
    pass_step(f"GET /conversations/{conversation_id}/messages")


def rename_conversation(conversation_id):
    title = f"Smoke conversation {datetime.now().strftime('%Y%m%d%H%M%S')}"
    response = request(
        "PATCH",
        f"/conversations/{conversation_id}",
        json={
            "title": title,
        },
    )
    data = expect_ok_json(response, f"PATCH /conversations/{conversation_id}")
    conversation = data.get("conversation", {})

    if conversation.get("title") != title:
        fail_step("PATCH conversation: title did not update", response)

    print(
        "PATCH conversation summary="
        f"id={conversation_id}, title={title!r}"
    )
    pass_step(f"PATCH /conversations/{conversation_id}")
    return title


def check_renamed_title(conversation_id, expected_title):
    response = request("GET", "/conversations")
    data = expect_ok_json(response, "GET /conversations after rename")
    conversation = find_conversation(data.get("conversations", []), conversation_id)

    if conversation is None:
        fail_step("GET /conversations after rename: conversation missing", response)

    if conversation.get("title") != expected_title:
        fail_step("GET /conversations after rename: title mismatch", response)

    print(
        "GET /conversations after rename summary="
        f"id={conversation_id}, title={conversation.get('title')!r}"
    )
    pass_step("GET /conversations confirms renamed title")


def delete_conversation(conversation_id):
    response = request("DELETE", f"/conversations/{conversation_id}")
    data = expect_ok_json(response, f"DELETE /conversations/{conversation_id}")

    if data.get("conversation_id") != conversation_id:
        fail_step("DELETE conversation: response id mismatch", response)

    print(f"DELETE conversation summary=id={conversation_id}")
    pass_step(f"DELETE /conversations/{conversation_id}")


def check_deleted(conversation_id):
    response = request("GET", "/conversations")
    data = expect_ok_json(response, "GET /conversations after delete")
    conversation = find_conversation(data.get("conversations", []), conversation_id)

    if conversation is not None:
        fail_step("GET /conversations after delete: conversation still exists", response)

    print(f"GET /conversations after delete summary=deleted_id={conversation_id}")
    pass_step("GET /conversations confirms deleted")


def main():
    print(f"API_BASE={API_BASE}")
    check_models()
    conversation_id, assistant_message_id = create_conversation_via_chat()
    check_conversation_exists(conversation_id)
    check_messages(conversation_id, assistant_message_id)
    title = rename_conversation(conversation_id)
    check_renamed_title(conversation_id, title)
    delete_conversation(conversation_id)
    check_deleted(conversation_id)
    pass_step("Conversation API smoke test complete")


if __name__ == "__main__":
    main()
