import os
import subprocess
import sys
import time
from pathlib import Path

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python"
PYTHON_BIN = os.getenv(
    "MINI_CHATCHAT_PYTHON",
    str(DEFAULT_VENV_PYTHON) if DEFAULT_VENV_PYTHON.exists() else sys.executable,
)
API_BASE = os.getenv(
    "MINI_CHATCHAT_API_BASE",
    "http://127.0.0.1:8000",
).rstrip("/")

SMOKE_TESTS = [
    "scripts/test_llm_provider.py",
    "scripts/test_react_core_api_smoke.py",
    "scripts/test_conversation_api_smoke.py",
    "scripts/test_auth_session_smoke.py",
    "scripts/test_account_session_smoke.py",
    "scripts/test_oauth_smoke.py",
    "scripts/test_email_auth_isolation_smoke.py",
    "scripts/test_temp_kb_api_smoke.py",
    "scripts/test_hybrid_search_smoke.py",
    "scripts/test_metadata_filter_smoke.py",
    "scripts/test_request_validation_smoke.py",
    "scripts/test_agent_stop_guard.py",
    "scripts/test_agent_nonblocking_smoke.py",
    "scripts/test_context_dedup_smoke.py",
    "scripts/test_context_token_budget_smoke.py",
    "scripts/test_rag_context_alignment.py",
    "scripts/test_kb_import_export.py",
    "scripts/test_search_time_routing_smoke.py",
    "scripts/test_tool_registry_smoke.py",
    "scripts/test_agent_tool_calling_smoke.py",
    "scripts/test_agent_loop_smoke.py",
    "scripts/test_multi_step_agent_smoke.py",
    "scripts/test_agent_planner_smoke.py",
    "scripts/test_agent_streaming_smoke.py",
    "scripts/test_agent_trace_persistence_smoke.py",
    "scripts/test_mcp_adapter_smoke.py",
    "scripts/test_real_mcp_integration_smoke.py",
    "scripts/test_real_mcp_transport_smoke.py",
    "scripts/test_sqlite_mcp_readonly_smoke.py",
    "scripts/test_filesystem_mcp_readonly_smoke.py",
    "scripts/test_sqlite_tool_smoke.py",
    "scripts/test_filesystem_tool_smoke.py",
    "scripts/test_browser_read_tool_smoke.py",
    "scripts/test_browser_search_tool_smoke.py",
]


def check_backend():
    """负责 check_backend 的函数职责。"""
    try:
        response = requests.get(f"{API_BASE}/models", timeout=5)
        if response.status_code == 200:
            print(f"[PASS] Backend reachable at {API_BASE}")
            return True

        print(
            f"[WARN] Backend responded at {API_BASE} "
            f"with HTTP {response.status_code}"
        )
        return False
    except requests.ConnectionError:
        print(f"[FAIL] Backend is not running at {API_BASE}")
        print("Start the backend before running smoke tests.")
        return False
    except requests.RequestException as exc:
        print(f"[WARN] Backend health check failed: {exc}")
        return False


def run_script(script_path):
    """负责 run_script 的函数职责。"""
    started_at = time.monotonic()
    print(f"\n=== RUN {script_path} ===")

    result = subprocess.run(
        [PYTHON_BIN, script_path],
        cwd=ROOT_DIR,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
    )

    elapsed = time.monotonic() - started_at
    output = (result.stdout or "") + (result.stderr or "")

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    if result.returncode == 0 and "[SKIP]" in output:
        status = "SKIP"
    elif result.returncode == 0:
        status = "PASS"
    elif any(
        marker in output
        for marker in (
            "ModuleNotFoundError",
            "ImportError",
            "Backend is not running",
            "Connection refused",
            "Name or service not known",
        )
    ):
        status = "ENVIRONMENT ERROR"
    else:
        status = "FAIL"

    print(f"=== {status} {script_path} ({elapsed:.1f}s) ===")

    return {
        "script": script_path,
        "status": status,
        "returncode": result.returncode,
        "elapsed": elapsed,
    }


def main():
    """负责 main 的函数职责。"""
    print(f"API_BASE={API_BASE}")
    print(f"PYTHON_BIN={PYTHON_BIN}")

    if not check_backend():
        print("[ENVIRONMENT ERROR] Backend must be running before smoke tests.")
        sys.exit(1)

    started_at = time.monotonic()
    results = []

    for script_path in SMOKE_TESTS:
        full_path = ROOT_DIR / script_path

        if not full_path.exists():
            print(f"\n=== FAIL {script_path} ===")
            print(f"[FAIL] missing script: {full_path}")
            results.append({
                "script": script_path,
                "status": "FAIL",
                "returncode": 1,
                "elapsed": 0,
            })
            continue

        results.append(run_script(script_path))

    total_elapsed = time.monotonic() - started_at
    failed = [result for result in results if result["status"] == "FAIL"]
    environment_errors = [
        result for result in results if result["status"] == "ENVIRONMENT ERROR"
    ]
    skipped = [result for result in results if result["status"] == "SKIP"]

    print("\n=== Smoke Test Summary ===")
    for result in results:
        print(
            f"[{result['status']}] {result['script']} "
            f"({result['elapsed']:.1f}s)"
        )

    print(f"Total tests: {len(results)}")
    print(f"PASS: {sum(1 for result in results if result['status'] == 'PASS')}")
    print(f"FAIL: {len(failed)}")
    print(f"SKIP: {len(skipped)}")
    print(f"ENVIRONMENT ERROR: {len(environment_errors)}")
    print(f"Total elapsed: {total_elapsed:.1f}s")

    if failed:
        print("\nFailed scripts:")
        for result in failed:
            print(
                f"- {result['script']} "
                f"(exit code {result['returncode']})"
            )
        sys.exit(1)

    if environment_errors:
        print("\nEnvironment error scripts:")
        for result in environment_errors:
            print(
                f"- {result['script']} "
                f"(exit code {result['returncode']})"
            )
        sys.exit(1)

    print("\nAll smoke tests passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
