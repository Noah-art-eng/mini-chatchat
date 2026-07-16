import os
import sys
import tempfile
from pathlib import Path

import requests


API_BASE = os.getenv(
    "MINI_CHATCHAT_API_BASE",
    "http://127.0.0.1:8000",
).rstrip("/")

ROOT_DIR = Path(__file__).resolve().parents[1]
SAMPLE_FILE = ROOT_DIR / "test_files" / "sample_rag.txt"
LOCAL_TEST_KB = "e2e_metadata_filter_test"

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


def write_local_test_files(temp_dir):
    alpha = Path(temp_dir) / "metadata_alpha.txt"
    beta = Path(temp_dir) / "metadata_beta.txt"

    alpha.write_text(
        "metadata filter shared topic alpha source. "
        "Mini ChatChat local knowledge base alpha document.",
        encoding="utf-8",
    )
    beta.write_text(
        "metadata filter shared topic beta source. "
        "Mini ChatChat local knowledge base beta document.",
        encoding="utf-8",
    )

    return alpha, beta


def upload_file(path):
    with path.open("rb") as file:
        response = request(
            "POST",
            "/upload",
            files={"file": (path.name, file, "text/plain")},
        )

    expect_ok_json(response, f"POST /upload {path.name}")


def prepare_local_test_kb(temp_dir):
    delete_kb_if_exists(LOCAL_TEST_KB)
    create_and_switch_kb(LOCAL_TEST_KB)
    alpha, beta = write_local_test_files(temp_dir)
    upload_file(alpha)
    upload_file(beta)
    return alpha.name, beta.name


def kb_chat_return_direct(payload, step_name):
    response = request("POST", "/kb_chat", json=payload)
    data = expect_ok_json(response, step_name)
    sources = data.get("sources", [])

    if not sources:
        fail_step(f"{step_name}: missing sources", response)

    return sources, response


def source_names(sources):
    return {
        source
        for source in (
            item.get("source") or item.get("file_name") or item.get("url")
            for item in sources
        )
        if source
    }


def assert_only_source(sources, expected_source, step_name, response):
    actual_sources = source_names(sources)

    if actual_sources != {expected_source}:
        fail_step(
            f"{step_name}: expected only {expected_source}, got {actual_sources}",
            response,
        )

    first = sources[0]
    for key in ("source", "vector_distance", "bm25_score", "hybrid_score"):
        if key not in first:
            fail_step(f"{step_name}: missing source field {key}", response)


def check_local_without_filter(alpha_name, beta_name):
    sources, response = kb_chat_return_direct(
        {
            "mode": "local_kb",
            "kb_name": LOCAL_TEST_KB,
            "query": "metadata filter shared topic",
            "stream": False,
            "top_k": 5,
            "score_threshold": 0.8,
            "prompt_name": "default",
            "return_direct": True,
            "rerank": False,
            "rerank_top_n": 3,
        },
        "POST /kb_chat local_kb no filter",
    )

    actual_sources = source_names(sources)
    expected = {alpha_name, beta_name}

    if not expected.issubset(actual_sources):
        fail_step(
            f"POST /kb_chat local_kb no filter: expected both sources, got {actual_sources}",
            response,
        )

    print(f"local no-filter summary=sources={sorted(actual_sources)}")
    pass_step("POST /kb_chat local_kb no filter")


def check_local_file_name_filter(alpha_name):
    sources, response = kb_chat_return_direct(
        {
            "mode": "local_kb",
            "kb_name": LOCAL_TEST_KB,
            "query": "metadata filter shared topic",
            "stream": False,
            "top_k": 5,
            "score_threshold": 0.8,
            "prompt_name": "default",
            "return_direct": True,
            "file_name": alpha_name,
            "rerank": False,
            "rerank_top_n": 3,
        },
        "POST /kb_chat local_kb file_name filter",
    )
    assert_only_source(
        sources,
        alpha_name,
        "POST /kb_chat local_kb file_name filter",
        response,
    )
    pass_step("POST /kb_chat local_kb file_name filter")


def check_local_source_filter(beta_name):
    sources, response = kb_chat_return_direct(
        {
            "mode": "local_kb",
            "kb_name": LOCAL_TEST_KB,
            "query": "metadata filter shared topic",
            "stream": False,
            "top_k": 5,
            "score_threshold": 0.8,
            "prompt_name": "default",
            "return_direct": True,
            "source": beta_name,
            "rerank": False,
            "rerank_top_n": 3,
        },
        "POST /kb_chat local_kb source filter",
    )
    assert_only_source(
        sources,
        beta_name,
        "POST /kb_chat local_kb source filter",
        response,
    )
    pass_step("POST /kb_chat local_kb source filter")


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


def check_temp_source_filter(temp_kb_id):
    sources, response = kb_chat_return_direct(
        {
            "mode": "temp_kb",
            "temp_kb_id": temp_kb_id,
            "query": "Mini ChatChat",
            "stream": False,
            "top_k": 3,
            "score_threshold": 0.8,
            "prompt_name": "default",
            "return_direct": True,
            "source": SAMPLE_FILE.name,
            "rerank": False,
            "rerank_top_n": 3,
        },
        "POST /kb_chat temp_kb source filter",
    )
    assert_only_source(
        sources,
        SAMPLE_FILE.name,
        "POST /kb_chat temp_kb source filter",
        response,
    )
    pass_step("POST /kb_chat temp_kb source filter")


def main():
    print(f"API_BASE={API_BASE}")
    should_cleanup = False

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            alpha_name, beta_name = prepare_local_test_kb(temp_dir)
            should_cleanup = True
            check_local_without_filter(alpha_name, beta_name)
            check_local_file_name_filter(alpha_name)
            check_local_source_filter(beta_name)

        temp_kb_id = upload_temp_file()
        check_temp_source_filter(temp_kb_id)
        pass_step("Metadata filter smoke test complete")
    finally:
        if should_cleanup:
            delete_kb_if_exists(LOCAL_TEST_KB)


if __name__ == "__main__":
    main()
