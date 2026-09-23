import os
import sys

import requests


API_BASE = os.getenv(
    "MINI_CHATCHAT_API_BASE",
    "http://127.0.0.1:8000",
).rstrip("/")

FORBIDDEN_TEXT = (
    "OpenAI 401",
    "invalid_api_key",
)


def pass_step(message):
    """负责 pass_step 的函数职责。"""
    print(f"[PASS] {message}")


def fail_step(message, response=None):
    """负责 fail_step 的函数职责。"""
    print(f"[FAIL] {message}")

    if response is not None:
        print(f"status={response.status_code}")
        print(f"body={response.text[:1200]}")

    sys.exit(1)


def request(method, path, **kwargs):
    """负责 request 的函数职责。"""
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


def parse_json(response, step_name):
    """负责 parse_json 的函数职责。"""
    try:
        return response.json()
    except ValueError:
        fail_step(f"{step_name}: response is not JSON", response)


def assert_no_key_error(response, step_name):
    """负责 assert_no_key_error 的函数职责。"""
    body = response.text
    for text in FORBIDDEN_TEXT:
        if text.lower() in body.lower():
            fail_step(f"{step_name}: found forbidden text {text}", response)


def summarize_sources(sources):
    """负责 summarize_sources 的函数职责。"""
    if not sources:
        return "sources=0"

    first = sources[0]
    source = first.get("source") or first.get("file_name") or first.get("url")
    chunk = first.get("chunk") or first.get("content") or ""
    return (
        f"sources={len(sources)}, first_source={source}, "
        f"preview={chunk[:120]!r}"
    )


def expect_ok_json(response, step_name):
    """负责 expect_ok_json 的函数职责。"""
    assert_no_key_error(response, step_name)

    if response.status_code != 200:
        fail_step(f"{step_name}: HTTP status is not 200", response)

    data = parse_json(response, step_name)

    if data.get("error"):
        fail_step(f"{step_name}: response contains error", response)

    return data


def check_models():
    """负责 check_models 的函数职责。"""
    response = request("GET", "/models")
    data = expect_ok_json(response, "GET /models")
    chat = data.get("chat", {})

    provider = chat.get("provider", "unknown")
    model = chat.get("default_model", "unknown")
    base_url = chat.get("base_url", "")

    print(f"provider={provider}")
    print(f"model={model}")
    print(f"base_url={base_url}")
    pass_step(f"GET /models HTTP {response.status_code}")


def check_local_kb_answer():
    """负责 check_local_kb_answer 的函数职责。"""
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
        f"answer={answer[:160]!r}, {summarize_sources(data.get('sources', []))}"
    )
    pass_step(f"POST /kb_chat local_kb HTTP {response.status_code}")


def check_local_kb_return_direct():
    """负责 check_local_kb_return_direct 的函数职责。"""
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
    pass_step(f"POST /kb_chat return_direct HTTP {response.status_code}")


def check_search_engine():
    """负责 check_search_engine 的函数职责。"""
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
        f"answer={answer[:160]!r}, {summarize_sources(data.get('sources', []))}"
    )
    pass_step(f"POST /kb_chat search_engine HTTP {response.status_code}")


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    check_models()
    check_local_kb_answer()
    check_local_kb_return_direct()
    check_search_engine()
    pass_step("LLM provider smoke test complete")


if __name__ == "__main__":
    main()
