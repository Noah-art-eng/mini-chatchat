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
LOCAL_TEST_KB = "e2e_hybrid_search_test"

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


def assert_hybrid_sources(sources, step_name, response):
    if not sources:
        fail_step(f"{step_name}: missing sources", response)

    first = sources[0]
    missing = [
        key
        for key in ("bm25_score", "hybrid_score", "vector_distance")
        if key not in first
    ]

    if missing:
        fail_step(
            f"{step_name}: missing hybrid fields: {', '.join(missing)}",
            response,
        )

    source = first.get("source") or first.get("file_name") or first.get("url")
    print(
        f"{step_name} summary="
        f"sources={len(sources)}, first_source={source}, "
        f"bm25_score={first.get('bm25_score')}, "
        f"hybrid_score={first.get('hybrid_score')}"
    )


def delete_kb_if_exists(kb_name):
    response = request("DELETE", f"/knowledge_bases/{kb_name}")

    if response.status_code >= 400:
        fail_step(f"DELETE /knowledge_bases/{kb_name}", response)

    pass_step(f"delete existing KB if present: {kb_name}")


def create_and_switch_kb(kb_name):
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
    delete_kb_if_exists(LOCAL_TEST_KB)
    create_and_switch_kb(LOCAL_TEST_KB)
    upload_sample_to_current_kb()


def check_local_kb_hybrid(kb_name):
    payload = {
        "mode": "local_kb",
        "kb_name": kb_name,
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
    data = expect_ok_json(response, "POST /kb_chat local_kb hybrid")
    assert_hybrid_sources(
        data.get("sources", []),
        "POST /kb_chat local_kb hybrid",
        response,
    )
    pass_step("POST /kb_chat local_kb hybrid")


def upload_temp_file():
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


def check_temp_kb_hybrid(temp_kb_id):
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
    data = expect_ok_json(response, "POST /kb_chat temp_kb hybrid")
    assert_hybrid_sources(
        data.get("sources", []),
        "POST /kb_chat temp_kb hybrid",
        response,
    )
    pass_step("POST /kb_chat temp_kb hybrid")


def main():
    print(f"API_BASE={API_BASE}")
    should_cleanup = False

    try:
        prepare_local_test_kb()
        should_cleanup = True
        check_local_kb_hybrid(LOCAL_TEST_KB)
        temp_kb_id = upload_temp_file()
        check_temp_kb_hybrid(temp_kb_id)
        pass_step("Hybrid search smoke test complete")
    finally:
        if should_cleanup:
            delete_kb_if_exists(LOCAL_TEST_KB)


if __name__ == "__main__":
    main()
