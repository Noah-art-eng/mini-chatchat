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
        print(f"body={response.text[:1800]}")

    sys.exit(1)


def request(method, path, **kwargs):
    try:
        return requests.request(
            method,
            f"{API_BASE}{path}",
            timeout=180,
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


def run_browser_read(arguments, step_name):
    response = request(
        "POST",
        "/agent/tools/browser_read/run",
        json={"arguments": arguments},
    )
    return expect_ok_json(response, step_name), response


def check_tool_is_listed():
    response = request("GET", "/agent/tools")
    data = expect_ok_json(response, "GET /agent/tools")
    names = {
        tool.get("name")
        for tool in data.get("tools", [])
    }

    if "browser_read" not in names:
        fail_step("browser_read missing from tool registry", response)

    print(f"tools summary={sorted(names)}")
    pass_step("GET /agent/tools includes browser_read")


def check_direct_browser_read_success():
    data, response = run_browser_read(
        {
            "url": "https://example.com",
            "max_chars": 4000,
        },
        "POST /agent/tools/browser_read/run example.com",
    )

    if not data.get("ok"):
        fail_step("browser_read example.com returned ok=false", response)

    result = data.get("result") or {}
    for key in ("title", "url", "text", "char_count", "truncated", "content_type"):
        if key not in result:
            fail_step(f"browser_read missing field: {key}", response)

    if "Example Domain" not in result.get("title", ""):
        fail_step("browser_read did not extract Example Domain title", response)

    if "Example Domain" not in result.get("text", ""):
        fail_step("browser_read did not extract visible page text", response)

    if result.get("content_type") != "text/html":
        fail_step("browser_read example.com content_type should be text/html", response)

    print(
        "browser_read summary="
        f"title={result.get('title')!r}, url={result.get('url')}, "
        f"chars={result.get('char_count')}, truncated={result.get('truncated')}"
    )
    pass_step("POST /agent/tools/browser_read/run stable public page")


def check_max_chars():
    data, response = run_browser_read(
        {
            "url": "https://www.iana.org/domains/example",
            "max_chars": 500,
        },
        "POST /agent/tools/browser_read/run max_chars",
    )

    if not data.get("ok"):
        fail_step("browser_read max_chars returned ok=false", response)

    result = data.get("result") or {}
    if result.get("char_count", 0) > 500:
        fail_step("browser_read exceeded max_chars", response)

    if not isinstance(result.get("truncated"), bool):
        fail_step("browser_read truncated must be boolean", response)

    print(
        "browser_read max_chars summary="
        f"chars={result.get('char_count')}, truncated={result.get('truncated')}"
    )
    pass_step("browser_read max_chars is enforced")


def check_rejected_url(url, expected_error, step_name):
    data, response = run_browser_read(
        {
            "url": url,
        },
        step_name,
    )

    if data.get("ok"):
        fail_step(f"{step_name}: unsafe URL was accepted", response)

    error = data.get("error") or ""
    if expected_error.lower() not in error.lower():
        fail_step(
            f"{step_name}: expected error containing {expected_error!r}, got {error!r}",
            response,
        )

    print(f"browser_read rejection summary=url={url!r}, error={error!r}")
    pass_step(step_name)


def check_binary_rejected():
    data, response = run_browser_read(
        {
            "url": "https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png",
        },
        "POST /agent/tools/browser_read/run binary",
    )

    if data.get("ok"):
        fail_step("browser_read accepted binary content", response)

    error = data.get("error") or ""
    if "unsupported content type" not in error.lower():
        fail_step("browser_read binary rejection has wrong error", response)

    print(f"browser_read binary summary=error={error!r}")
    pass_step("browser_read rejects binary content")


def check_redirect_to_private_rejected():
    data, response = run_browser_read(
        {
            "url": "https://postman-echo.com/redirect-to?url=http://127.0.0.1:8000",
        },
        "POST /agent/tools/browser_read/run redirect private",
    )

    if data.get("ok"):
        fail_step("browser_read accepted redirect to private address", response)

    error = data.get("error") or ""
    if "not public" not in error.lower() and "localhost" not in error.lower():
        fail_step("browser_read redirect rejection has wrong error", response)

    print(f"browser_read redirect summary=error={error!r}")
    pass_step("browser_read rejects redirect to private address")


def check_agent_run_browser_read():
    response = request(
        "POST",
        "/agent/run",
        json={
            "query": "Read https://example.com and summarize the page.",
            "kb_name": "default",
            "tools": ["browser_read"],
        },
    )
    data = expect_ok_json(response, "POST /agent/run browser_read")

    tool_call = data.get("tool_call") or {}
    tool_result = data.get("tool_result") or {}

    if tool_call.get("tool") != "browser_read":
        fail_step("agent did not choose browser_read", response)

    if not tool_result.get("ok"):
        fail_step("agent browser_read tool_result ok=false", response)

    result = tool_result.get("result") or {}
    if "Example Domain" not in result.get("title", ""):
        fail_step("agent browser_read result missing title", response)

    answer = data.get("answer") or ""
    if not answer.strip():
        fail_step("agent browser_read final answer missing", response)

    print(
        "agent browser_read summary="
        f"tool={tool_call.get('tool')}, title={result.get('title')!r}, "
        f"answer={answer[:120]!r}"
    )
    pass_step("POST /agent/run browser_read")


def main():
    print(f"API_BASE={API_BASE}")
    check_tool_is_listed()
    check_direct_browser_read_success()
    check_max_chars()
    check_rejected_url("http://localhost:8000", "internal hostnames", "localhost rejected")
    check_rejected_url("http://127.0.0.1:8000", "not public", "127.0.0.1 rejected")
    check_rejected_url("http://[::1]:8000", "not public", "::1 rejected")
    check_rejected_url("file:///etc/passwd", "only http and https", "file URL rejected")
    check_rejected_url("ftp://example.com/file.txt", "only http and https", "ftp URL rejected")
    check_rejected_url("http://10.0.0.1", "not public", "private IPv4 rejected")
    check_rejected_url("http://[fd00::1]", "not public", "private IPv6 rejected")
    check_rejected_url(
        "https://user:password@example.com",
        "username or password",
        "URL credentials rejected",
    )
    check_binary_rejected()
    check_redirect_to_private_rejected()
    check_agent_run_browser_read()
    pass_step("Browser read tool smoke test complete")


if __name__ == "__main__":
    main()
