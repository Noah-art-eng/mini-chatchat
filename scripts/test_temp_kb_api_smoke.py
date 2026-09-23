import os
import sys
from pathlib import Path

import requests


API_BASE = os.getenv(
    "MINI_CHATCHAT_API_BASE",
    "http://127.0.0.1:8000",
).rstrip("/")

ROOT_DIR = Path(__file__).resolve().parents[1]
SAMPLE_FILE = ROOT_DIR / "test_files" / "sample_rag.txt"

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


def assert_safe_response(response, step_name):
    """负责 assert_safe_response 的函数职责。"""
    for text in FORBIDDEN_TEXT:
        if text.lower() in response.text.lower():
            fail_step(f"{step_name}: forbidden text found: {text}", response)


def parse_json(response, step_name):
    """负责 parse_json 的函数职责。"""
    try:
        return response.json()
    except ValueError:
        fail_step(f"{step_name}: response is not JSON", response)


def expect_ok_json(response, step_name):
    """负责 expect_ok_json 的函数职责。"""
    assert_safe_response(response, step_name)

    if response.status_code != 200:
        fail_step(f"{step_name}: HTTP status is not 200", response)

    data = parse_json(response, step_name)

    if isinstance(data, dict) and data.get("error"):
        fail_step(f"{step_name}: response contains error", response)

    return data


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


def upload_temp_file():
    """负责 upload_temp_file 的函数职责。"""
    if not SAMPLE_FILE.exists():
        fail_step(f"missing test file: {SAMPLE_FILE}")

    with SAMPLE_FILE.open("rb") as file:
        response = request(
            "POST",
            "/temp_upload",
            files={"file": (SAMPLE_FILE.name, file, "text/plain")},
        )

    data = expect_ok_json(response, "POST /temp_upload")
    temp_kb_id = data.get("temp_kb_id") or data.get("temp_id") or data.get("kb_name")

    if not temp_kb_id:
        fail_step("POST /temp_upload: missing temp_kb_id", response)

    print(f"temp_upload summary=temp_kb_id={temp_kb_id}")
    pass_step("POST /temp_upload")
    return temp_kb_id


def check_temp_kb_return_direct(temp_kb_id):
    """负责 check_temp_kb_return_direct 的函数职责。"""
    payload = {
        "mode": "temp_kb",
        "temp_kb_id": temp_kb_id,
        "query": "Mini ChatChat",
        "stream": False,
        "top_k": 3,
        "score_threshold": 0.8,
        "prompt_name": "default",
        "return_direct": True,
        "rerank": False,
        "rerank_top_n": 3,
    }
    response = request("POST", "/kb_chat", json=payload)
    data = expect_ok_json(response, "POST /kb_chat temp_kb return_direct")
    sources = data.get("sources", [])

    if not sources:
        fail_step("POST /kb_chat temp_kb return_direct: missing sources", response)

    found = any(
        "Mini ChatChat" in (item.get("chunk") or item.get("content") or "")
        or "sample_rag" in (item.get("source") or item.get("file_name") or "")
        for item in sources
    )

    if not found:
        fail_step(
            "POST /kb_chat temp_kb return_direct: sample content not found",
            response,
        )

    print(f"temp_kb return_direct summary={summarize_sources(sources)}")
    pass_step("POST /kb_chat temp_kb return_direct")


def check_temp_kb_answer(temp_kb_id):
    """负责 check_temp_kb_answer 的函数职责。"""
    payload = {
        "mode": "temp_kb",
        "temp_kb_id": temp_kb_id,
        "query": "What does Mini ChatChat support?",
        "stream": False,
        "top_k": 3,
        "score_threshold": 0.8,
        "prompt_name": "default",
        "return_direct": False,
        "rerank": False,
        "rerank_top_n": 3,
    }
    response = request("POST", "/kb_chat", json=payload)
    data = expect_ok_json(response, "POST /kb_chat temp_kb")
    answer = data.get("answer") or data.get("content") or ""

    if not answer:
        fail_step("POST /kb_chat temp_kb: missing answer/content", response)

    print(
        "temp_kb answer summary="
        f"answer={answer[:160]!r}, {summarize_sources(data.get('sources', []))}"
    )
    pass_step("POST /kb_chat temp_kb")


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    temp_kb_id = upload_temp_file()
    check_temp_kb_return_direct(temp_kb_id)
    check_temp_kb_answer(temp_kb_id)
    pass_step("temp_kb API smoke test complete")


if __name__ == "__main__":
    main()
