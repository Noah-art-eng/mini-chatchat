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
            timeout=30,
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


def expect_ok_json(response, step_name):
    assert_safe_response(response, step_name)

    if response.status_code != 200:
        fail_step(f"{step_name}: HTTP status is not 200", response)

    try:
        return response.json()
    except ValueError:
        fail_step(f"{step_name}: response is not JSON", response)


def check_health():
    response = request("GET", "/health")
    data = expect_ok_json(response, "GET /health")

    if data.get("status") != "ok":
        fail_step("GET /health: status is not ok", response)

    if data.get("service") != "mini-chatchat":
        fail_step("GET /health: service mismatch", response)

    provider = data.get("provider")
    if provider not in ("deepseek", "openai", "none"):
        fail_step(f"GET /health: invalid provider {provider}", response)

    print(
        "health summary="
        f"status={data.get('status')}, "
        f"service={data.get('service')}, "
        f"version={data.get('version')}, "
        f"provider={provider}"
    )
    pass_step("GET /health")


def check_health_deps():
    response = request("GET", "/health/deps")
    data = expect_ok_json(response, "GET /health/deps")

    if data.get("status") not in ("ok", "degraded"):
        fail_step("GET /health/deps: invalid status", response)

    checks = data.get("checks")
    if not isinstance(checks, dict):
        fail_step("GET /health/deps: checks missing", response)

    required = (
        "database",
        "data_dir",
        "uploads_dir",
        "chat_provider",
        "embedding_model",
    )

    missing = [key for key in required if key not in checks]
    if missing:
        fail_step(
            f"GET /health/deps: missing checks: {', '.join(missing)}",
            response,
        )

    for key in required:
        if checks[key] not in ("ok", "error"):
            fail_step(
                f"GET /health/deps: invalid check value {key}={checks[key]}",
                response,
            )

    if data.get("status") == "ok" and any(
        checks[key] != "ok"
        for key in required
    ):
        fail_step("GET /health/deps: status ok but some checks failed", response)

    print(
        "health deps summary="
        f"status={data.get('status')}, "
        f"checks={checks}"
    )
    pass_step("GET /health/deps")


def main():
    print(f"API_BASE={API_BASE}")
    check_health()
    check_health_deps()
    pass_step("Health smoke test complete")


if __name__ == "__main__":
    main()
