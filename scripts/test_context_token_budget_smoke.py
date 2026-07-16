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
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from rag import build_context, estimate_tokens  # noqa: E402


LOCAL_TEST_KB = "e2e_context_token_budget_test"

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


def check_build_context_budget():
    results = [
        {
            "id": index + 1,
            "chunk": (
                f"budget chunk {index} "
                + "Mini ChatChat token budget context. " * 40
            ),
            "source": "budget.txt",
            "chunk_id": index + 1,
        }
        for index in range(10)
    ]

    full_context = build_context(results, context_token_budget=None)
    limited_context = build_context(results, context_token_budget=500)

    full_count = full_context.count("Source ")
    limited_count = limited_context.count("Source ")
    limited_tokens = estimate_tokens(limited_context)

    if full_count != len(results):
        fail_step("build_context without budget did not include all sources")

    if limited_count <= 0:
        fail_step("build_context budget removed all sources")

    if limited_count >= full_count:
        fail_step("build_context budget did not trim sources")

    if limited_tokens > 500:
        fail_step(
            f"build_context exceeded token budget: {limited_tokens} > 500"
        )

    print(
        "build_context summary="
        f"full_sources={full_count}, limited_sources={limited_count}, "
        f"limited_tokens={limited_tokens}"
    )
    pass_step("build_context token budget")


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


def write_long_test_file(temp_dir, filename):
    path = Path(temp_dir) / filename
    repeated = "\n".join(
        [
            (
                f"budget section {index}. "
                "Mini ChatChat context token budget should keep prompt small. "
                "This long file exists to create many retrieval chunks."
            )
            for index in range(120)
        ]
    )
    path.write_text(repeated, encoding="utf-8")
    return path


def upload_file_to_current_kb(path):
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
    long_file = write_long_test_file(temp_dir, "budget_long_local.txt")
    upload_file_to_current_kb(long_file)
    return long_file.name


def check_local_kb_answer():
    payload = {
        "mode": "local_kb",
        "kb_name": LOCAL_TEST_KB,
        "query": "What should the context token budget do?",
        "stream": False,
        "top_k": 20,
        "score_threshold": 0.8,
        "prompt_name": "default",
        "return_direct": False,
        "rerank": False,
        "rerank_top_n": 3,
    }
    response = request("POST", "/kb_chat", json=payload)
    data = expect_ok_json(response, "POST /kb_chat local_kb token budget")
    answer = data.get("answer") or data.get("content") or ""

    if not answer:
        fail_step("POST /kb_chat local_kb token budget: missing answer", response)

    print(
        "local_kb token budget summary="
        f"answer={answer[:120]!r}, sources={len(data.get('sources', []))}"
    )
    pass_step("POST /kb_chat local_kb token budget")


def upload_temp_file(path):
    with path.open("rb") as file:
        response = request(
            "POST",
            "/temp_upload",
            files={"file": (path.name, file, "text/plain")},
        )

    data = expect_ok_json(response, "POST /temp_upload")
    temp_kb_id = data.get("temp_kb_id") or data.get("temp_id") or data.get("kb_name")

    if not temp_kb_id:
        fail_step("POST /temp_upload: missing temp_kb_id", response)

    print(f"temp_upload summary=temp_kb_id={temp_kb_id}")
    pass_step("POST /temp_upload")
    return temp_kb_id


def check_temp_kb_answer(temp_kb_id):
    payload = {
        "mode": "temp_kb",
        "temp_kb_id": temp_kb_id,
        "query": "What should the context token budget do?",
        "stream": False,
        "top_k": 20,
        "score_threshold": 0.8,
        "prompt_name": "default",
        "return_direct": False,
        "rerank": False,
        "rerank_top_n": 3,
    }
    response = request("POST", "/kb_chat", json=payload)
    data = expect_ok_json(response, "POST /kb_chat temp_kb token budget")
    answer = data.get("answer") or data.get("content") or ""

    if not answer:
        fail_step("POST /kb_chat temp_kb token budget: missing answer", response)

    print(
        "temp_kb token budget summary="
        f"answer={answer[:120]!r}, sources={len(data.get('sources', []))}"
    )
    pass_step("POST /kb_chat temp_kb token budget")


def main():
    print(f"API_BASE={API_BASE}")
    check_build_context_budget()
    should_cleanup = False

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            prepare_local_test_kb(temp_dir)
            should_cleanup = True
            check_local_kb_answer()

            temp_file = write_long_test_file(temp_dir, "budget_long_temp.txt")
            temp_kb_id = upload_temp_file(temp_file)
            check_temp_kb_answer(temp_kb_id)

        pass_step("Context token budget smoke test complete")
    finally:
        if should_cleanup:
            delete_kb_if_exists(LOCAL_TEST_KB)


if __name__ == "__main__":
    main()
