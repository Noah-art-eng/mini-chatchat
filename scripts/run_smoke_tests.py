import os
import subprocess
import sys
import time
from pathlib import Path

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
API_BASE = os.getenv(
    "MINI_CHATCHAT_API_BASE",
    "http://127.0.0.1:8000",
).rstrip("/")

SMOKE_TESTS = [
    "scripts/test_llm_provider.py",
    "scripts/test_react_core_api_smoke.py",
    "scripts/test_conversation_api_smoke.py",
    "scripts/test_temp_kb_api_smoke.py",
    "scripts/test_hybrid_search_smoke.py",
    "scripts/test_metadata_filter_smoke.py",
    "scripts/test_context_dedup_smoke.py",
    "scripts/test_context_token_budget_smoke.py",
    "scripts/test_kb_import_export.py",
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
    started_at = time.monotonic()
    print(f"\n=== RUN {script_path} ===")

    result = subprocess.run(
        [sys.executable, script_path],
        cwd=ROOT_DIR,
        env=os.environ.copy(),
        text=True,
    )

    elapsed = time.monotonic() - started_at
    status = "PASS" if result.returncode == 0 else "FAIL"
    print(f"=== {status} {script_path} ({elapsed:.1f}s) ===")

    return {
        "script": script_path,
        "status": status,
        "returncode": result.returncode,
        "elapsed": elapsed,
    }


def main():
    print(f"API_BASE={API_BASE}")
    check_backend()

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
    failed = [result for result in results if result["status"] != "PASS"]

    print("\n=== Smoke Test Summary ===")
    for result in results:
        print(
            f"[{result['status']}] {result['script']} "
            f"({result['elapsed']:.1f}s)"
        )

    print(f"Total tests: {len(results)}")
    print(f"Total elapsed: {total_elapsed:.1f}s")

    if failed:
        print("\nFailed scripts:")
        for result in failed:
            print(
                f"- {result['script']} "
                f"(exit code {result['returncode']})"
            )
        sys.exit(1)

    print("\nAll smoke tests passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
