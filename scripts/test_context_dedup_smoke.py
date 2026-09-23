import os
import sys
from pathlib import Path

import requests

from smoke_auth import auth_headers


API_BASE = os.getenv(
    "MINI_CHATCHAT_API_BASE",
    "http://127.0.0.1:8000",
).rstrip("/")

ROOT_DIR = Path(__file__).resolve().parents[1]
SAMPLE_FILE = ROOT_DIR / "test_files" / "sample_rag.txt"
LOCAL_TEST_KB = "e2e_context_dedup_test"

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
    headers = kwargs.pop("headers", {})
    headers = {**auth_headers(), **headers}

    try:
        return requests.request(
            method,
            f"{API_BASE}{path}",
            headers=headers,
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


def delete_kb_if_exists(kb_name):
    """负责 delete_kb_if_exists 的函数职责。"""
    response = request("DELETE", f"/knowledge_bases/{kb_name}")

    if response.status_code == 404:
        pass_step(f"delete existing KB if present: {kb_name}")
        return

    if response.status_code >= 400:
        fail_step(f"DELETE /knowledge_bases/{kb_name}", response)

    pass_step(f"delete existing KB if present: {kb_name}")


def create_and_switch_kb(kb_name):
    """负责 create_and_switch_kb 的函数职责。"""
    response = request(
        "POST",
        "/knowledge_bases",
        json={"kb_name": kb_name},
    )
    expect_ok_json(response, f"POST /knowledge_bases {kb_name}")

    response = request(
        "POST",
        "/switch_kb",
        json={"kb_name": kb_name},
    )
    expect_ok_json(response, f"POST /switch_kb {kb_name}")


def upload_sample_to_current_kb():
    """负责 upload_sample_to_current_kb 的函数职责。"""
    if not SAMPLE_FILE.exists():
        fail_step(f"missing test file: {SAMPLE_FILE}")

    with SAMPLE_FILE.open("rb") as file:
        response = request(
            "POST",
            "/upload",
            files={"file": (SAMPLE_FILE.name, file, "text/plain")},
        )

    expect_ok_json(response, "POST /upload sample_rag.txt")


def prepare_local_test_kb():
    """负责 prepare_local_test_kb 的函数职责。"""
    delete_kb_if_exists(LOCAL_TEST_KB)
    create_and_switch_kb(LOCAL_TEST_KB)
    upload_sample_to_current_kb()


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


def result_key(source):
    """负责 result_key 的函数职责。"""
    source_name = source.get("source") or source.get("file_name") or source.get("url")
    chunk_id = source.get("chunk_id")

    if chunk_id is not None:
        return (source_name, chunk_id)

    return (source_name, source.get("chunk") or source.get("content") or "")


def assert_deduped_sources(sources, step_name, response):
    """负责 assert_deduped_sources 的函数职责。"""
    if not sources:
        fail_step(f"{step_name}: missing sources", response)

    keys = [result_key(source) for source in sources]

    if len(keys) != len(set(keys)):
        fail_step(f"{step_name}: duplicate source+chunk_id found", response)

    first = sources[0]
    missing = [
        key
        for key in ("source", "vector_distance", "bm25_score", "hybrid_score")
        if key not in first
    ]

    if missing:
        fail_step(
            f"{step_name}: missing fields: {', '.join(missing)}",
            response,
        )

    print(
        f"{step_name} summary="
        f"sources={len(sources)}, unique_keys={len(set(keys))}, "
        f"first_source={first.get('source')}, "
        f"hybrid_score={first.get('hybrid_score')}"
    )


def check_local_kb_dedup():
    """负责 check_local_kb_dedup 的函数职责。"""
    payload = {
        "mode": "local_kb",
        "kb_name": LOCAL_TEST_KB,
        "query": "Mini ChatChat",
        "stream": False,
        "top_k": 10,
        "score_threshold": 0.8,
        "prompt_name": "default",
        "return_direct": True,
        "rerank": False,
        "rerank_top_n": 3,
    }
    response = request("POST", "/kb_chat", json=payload)
    data = expect_ok_json(response, "POST /kb_chat local_kb dedup")
    assert_deduped_sources(
        data.get("sources", []),
        "POST /kb_chat local_kb dedup",
        response,
    )
    pass_step("POST /kb_chat local_kb dedup")


def check_temp_kb_dedup(temp_kb_id):
    """负责 check_temp_kb_dedup 的函数职责。"""
    payload = {
        "mode": "temp_kb",
        "temp_kb_id": temp_kb_id,
        "query": "Mini ChatChat",
        "stream": False,
        "top_k": 10,
        "score_threshold": 0.8,
        "prompt_name": "default",
        "return_direct": True,
        "rerank": False,
        "rerank_top_n": 3,
    }
    response = request("POST", "/kb_chat", json=payload)
    data = expect_ok_json(response, "POST /kb_chat temp_kb dedup")
    assert_deduped_sources(
        data.get("sources", []),
        "POST /kb_chat temp_kb dedup",
        response,
    )
    pass_step("POST /kb_chat temp_kb dedup")


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    should_cleanup = False

    try:
        prepare_local_test_kb()
        should_cleanup = True
        check_local_kb_dedup()
        temp_kb_id = upload_temp_file()
        check_temp_kb_dedup(temp_kb_id)
        pass_step("Context dedup smoke test complete")
    finally:
        if should_cleanup:
            delete_kb_if_exists(LOCAL_TEST_KB)


if __name__ == "__main__":
    main()
