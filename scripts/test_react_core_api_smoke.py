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


def summarize_sources(sources):
    if not sources:
        return "sources=0"

    first = sources[0]
    source = first.get("source") or first.get("file_name") or first.get("url")
    return f"sources={len(sources)}, first_source={source}"


def check_models():
    response = request("GET", "/models")
    data = expect_ok_json(response, "GET /models")
    chat = data.get("chat", {})
    print(
        "models summary="
        f"provider={chat.get('provider')}, "
        f"model={chat.get('default_model')}, "
        f"base_url={chat.get('base_url')}"
    )
    pass_step("GET /models")


def check_kb_chat_local():
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
    answer = data.get("answer") or data.get("content") or ""

    if not answer:
        fail_step("POST /kb_chat local_kb: missing answer/content", response)

    print(
        "local_kb summary="
        f"answer={answer[:120]!r}, {summarize_sources(data.get('sources', []))}"
    )
    pass_step("POST /kb_chat local_kb")


def check_kb_chat_return_direct():
    payload = {
        "mode": "local_kb",
        "kb_name": "default",
        "query": "Docker",
        "stream": False,
        "top_k": 3,
        "score_threshold": 0.8,
        "prompt_name": "default",
        "return_direct": True,
        "rerank": False,
        "rerank_top_n": 3,
    }
    response = request("POST", "/kb_chat", json=payload)
    data = expect_ok_json(response, "POST /kb_chat return_direct")
    sources = data.get("sources", [])

    if not sources:
        fail_step("POST /kb_chat return_direct: missing sources", response)

    print(f"return_direct summary={summarize_sources(sources)}")
    pass_step("POST /kb_chat return_direct")


def check_kb_chat_search_engine():
    payload = {
        "mode": "search_engine",
        "query": "latest OpenAI news",
        "stream": False,
        "top_k": 3,
        "score_threshold": 0.8,
        "prompt_name": "default",
        "return_direct": False,
        "rerank": False,
        "rerank_top_n": 3,
    }
    response = request("POST", "/kb_chat", json=payload)
    data = expect_ok_json(response, "POST /kb_chat search_engine")
    answer = data.get("answer") or data.get("content") or ""

    if not answer:
        fail_step("POST /kb_chat search_engine: missing answer/content", response)

    print(
        "search_engine summary="
        f"answer={answer[:120]!r}, {summarize_sources(data.get('sources', []))}"
    )
    pass_step("POST /kb_chat search_engine")


def check_conversations():
    response = request("GET", "/conversations")
    data = expect_ok_json(response, "GET /conversations")
    conversations = data.get("conversations", [])
    print(f"conversations summary=count={len(conversations)}")
    pass_step("GET /conversations")


def check_knowledge_bases():
    response = request("GET", "/knowledge_bases")
    data = expect_ok_json(response, "GET /knowledge_bases")
    kbs = data.get("knowledge_bases", [])
    print(f"knowledge_bases summary=count={len(kbs)}")
    pass_step("GET /knowledge_bases")


def check_documents():
    response = request("GET", "/documents")
    data = expect_ok_json(response, "GET /documents")
    files = data.get("files", [])
    print(f"documents summary=count={len(files)}")
    pass_step("GET /documents")


def main():
    print(f"API_BASE={API_BASE}")
    check_models()
    check_kb_chat_local()
    check_kb_chat_return_direct()
    check_kb_chat_search_engine()
    check_conversations()
    check_knowledge_bases()
    check_documents()
    pass_step("React core API smoke test complete")


if __name__ == "__main__":
    main()
