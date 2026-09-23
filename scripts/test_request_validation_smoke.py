"""Check that RAG request validation rejects invalid numeric boundaries."""

import os
import sys

import requests

from smoke_auth import auth_headers


API_BASE = os.getenv("MINI_CHATCHAT_API_BASE", "http://127.0.0.1:8000").rstrip("/")


def fail(message, response=None):
    """负责 fail 的函数职责。"""
    print(f"[FAIL] {message}")
    if response is not None:
        print(f"status={response.status_code} body={response.text[:500]}")
    sys.exit(1)


def expect_validation_error(label, method, path, **kwargs):
    """负责 expect_validation_error 的函数职责。"""
    response = requests.request(
        method,
        f"{API_BASE}{path}",
        headers=auth_headers(),
        timeout=30,
        **kwargs,
    )
    if response.status_code != 422:
        fail(f"{label}: expected HTTP 422", response)
    print(f"[PASS] {label}")


def main():
    """负责 main 的函数职责。"""
    expect_validation_error(
        "KB chat rejects top_k=0",
        "POST",
        "/kb_chat",
        json={"query": "test", "top_k": 0},
    )
    expect_validation_error(
        "KB chat rejects negative score_threshold",
        "POST",
        "/kb_chat",
        json={"query": "test", "score_threshold": -0.1},
    )
    expect_validation_error(
        "KB chat rejects oversized rerank_top_n",
        "POST",
        "/kb_chat",
        json={"query": "test", "rerank_top_n": 21},
    )
    expect_validation_error(
        "Search docs rejects top_k=21",
        "POST",
        "/search_docs",
        json={"query": "test", "top_k": 21},
    )
    expect_validation_error(
        "OpenAI-compatible chat rejects invalid extra_body top_k",
        "POST",
        "/chat/completions",
        json={
            "messages": [{"role": "user", "content": "test"}],
            "extra_body": {"top_k": 0},
        },
    )
    expect_validation_error(
        "Temp upload rejects chunk_size=0",
        "POST",
        "/temp_upload",
        files={"file": ("test.txt", b"test", "text/plain")},
        data={"chunk_size": "0", "chunk_overlap": "0"},
    )
    expect_validation_error(
        "Temp upload rejects overlap equal to chunk_size",
        "POST",
        "/temp_upload",
        files={"file": ("test.txt", b"test", "text/plain")},
        data={"chunk_size": "10", "chunk_overlap": "10"},
    )


if __name__ == "__main__":
    main()
