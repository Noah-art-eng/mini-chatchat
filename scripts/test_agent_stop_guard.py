"""Regression check: a cancelled Agent run must not start later stages."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import agent_service  # noqa: E402


class AgentStopGuardTest(unittest.TestCase):
    """负责 AgentStopGuardTest 的类职责。"""
    def test_stopped_run_skips_tool_and_final_answer_generation(self):
        """负责 test_stopped_run_skips_tool_and_final_answer_generation 的函数职责。"""
        with (
            patch.object(
                agent_service,
                "get_available_tool_specs",
                return_value=([{"name": "calculator"}], None),
            ),
            patch.object(agent_service, "run_tool") as run_tool,
            patch.object(
                agent_service,
                "generate_multi_step_final_answer",
            ) as generate_final_answer,
        ):
            result = agent_service.run_agent_multi_step(
                "1 + 1",
                tools=["calculator"],
                should_stop=lambda: True,
            )

        run_tool.assert_not_called()
        generate_final_answer.assert_not_called()
        self.assertEqual(result["error"], "client disconnected")
        self.assertEqual(result["answer"], "")

    def test_disconnect_after_decision_skips_next_tool_and_final_answer(self):
        """负责 test_disconnect_after_decision_skips_next_tool_and_final_answer 的函数职责。"""
        checks = 0

        def should_stop():
            """负责 should_stop 的函数职责。"""
            nonlocal checks
            checks += 1
            return checks >= 2

        with (
            patch.object(
                agent_service,
                "get_available_tool_specs",
                return_value=([{"name": "calculator"}], None),
            ),
            patch.object(
                agent_service,
                "decide_agent_action",
                return_value={
                    "action": {
                        "action": "tool",
                        "tool": "calculator",
                        "arguments": {"expression": "1+1"},
                        "reason": "test",
                        "final_answer": None,
                    },
                    "error": None,
                },
            ),
            patch.object(agent_service, "run_tool") as run_tool,
            patch.object(
                agent_service,
                "generate_multi_step_final_answer",
            ) as generate_final_answer,
        ):
            result = agent_service.run_agent_multi_step(
                "1 + 1",
                tools=["calculator"],
                should_stop=should_stop,
            )

        run_tool.assert_not_called()
        generate_final_answer.assert_not_called()
        self.assertEqual(result["error"], "client disconnected")


if __name__ == "__main__":
    unittest.main()
