"""Regression checks for Agent request isolation without a real LLM or MCP server."""

import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
import sys

sys.path.insert(0, str(BACKEND_DIR))

import app  # noqa: E402


class AgentNonblockingSmokeTest(unittest.TestCase):
    """负责 AgentNonblockingSmokeTest 的类职责。"""
    def test_slow_agent_does_not_delay_tool_listing(self):
        """负责 test_slow_agent_does_not_delay_tool_listing 的函数职责。"""
        started = threading.Event()
        release = threading.Event()
        response_holder = {}

        def slow_agent(*_args, **_kwargs):
            """负责 slow_agent 的函数职责。"""
            started.set()
            if not release.wait(timeout=2):
                raise TimeoutError("fake agent did not release")
            return {"answer": "done", "trace": []}

        with (
            patch.object(app, "run_agent_persisted", side_effect=slow_agent),
            patch.object(app, "list_all_tools", return_value=[]),
            patch.object(app, "require_permission"),
        ):
            with TestClient(app.app) as client:
                worker = threading.Thread(
                    target=lambda: response_holder.setdefault(
                        "response",
                        client.post("/agent/run", json={"query": "slow test"}),
                    ),
                )
                worker.start()
                self.assertTrue(started.wait(timeout=1))

                started_at = time.monotonic()
                tools_response = client.get("/agent/tools")
                self.assertLess(time.monotonic() - started_at, 0.5)
                self.assertEqual(tools_response.status_code, 200)

                release.set()
                worker.join(timeout=2)
                self.assertFalse(worker.is_alive())
                self.assertEqual(response_holder["response"].status_code, 200)

    def test_explicit_local_tool_skips_mcp_discovery(self):
        """负责 test_explicit_local_tool_skips_mcp_discovery 的函数职责。"""
        with patch("agent_service.list_all_tools") as list_all:
            tools, error = app.get_available_tool_specs(["kb_search"])

        self.assertIsNone(error)
        self.assertEqual([tool["name"] for tool in tools], ["kb_search"])
        list_all.assert_not_called()

    def test_llm_client_disables_retry_amplification(self):
        """负责 test_llm_client_disables_retry_amplification 的函数职责。"""
        client = app.get_openai_client()
        self.assertEqual(client.max_retries, 0)


if __name__ == "__main__":
    unittest.main()
