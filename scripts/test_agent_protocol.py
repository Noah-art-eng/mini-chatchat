"""验证 Agent prompt 与结构化输出协议拆分前后保持兼容。"""

import hashlib
import json
import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import agent_protocol  # noqa: E402
import agent_service  # noqa: E402


class PublicTool:
    """模拟工具注册表对象，确认 prompt 仍只使用公开字段。"""

    def public_dict(self):
        """返回 Agent prompt 可以看到的工具描述。"""
        return {
            "name": "calculator",
            "description": "calc",
            "parameters": {"type": "object"},
        }


class AgentProtocolTest(unittest.TestCase):
    """覆盖 Agent JSON 解析、计划规范化、prompt 和兼容导出。"""

    def test_parse_tool_call_accepts_plain_fenced_and_extra_text_json(self):
        """工具选择 JSON 被代码块或说明文字包围时仍按旧规则提取。"""
        expected = {
            "tool": "calculator",
            "arguments": {"expression": "1+1"},
            "reason": "math",
        }
        payload = json.dumps(expected)

        for text in (payload, f"```json\n{payload}\n```", f"prefix {payload} suffix"):
            with self.subTest(text=text):
                result, error = agent_protocol.parse_tool_call(text)
                self.assertIsNone(error)
                self.assertEqual(result, expected)

    def test_parse_tool_call_rejects_malformed_or_unexpected_data(self):
        """非法 JSON、非对象参数和额外字段不能进入工具执行阶段。"""
        cases = (
            ("{broken", "invalid JSON tool call:"),
            ('{"tool":"calculator","arguments":[]}', "arguments must be an object"),
            ('{"tool":"calculator","extra":true}', "unexpected tool call keys: extra"),
        )

        for text, expected_error in cases:
            with self.subTest(text=text):
                result, error = agent_protocol.parse_tool_call(text)
                self.assertIsNone(result)
                self.assertIn(expected_error, error)

    def test_parse_agent_action_normalizes_final_action(self):
        """final 动作继续清空工具和参数，同时保留模型给出的最终回答。"""
        result, error = agent_protocol.parse_agent_action(json.dumps({
            "action": "final",
            "tool": "calculator",
            "arguments": {"expression": "1+1"},
            "reason": "done",
            "final_answer": "2",
        }))

        self.assertIsNone(error)
        self.assertEqual(result["tool"], "none")
        self.assertEqual(result["arguments"], {})
        self.assertEqual(result["final_answer"], "2")

    def test_parse_agent_action_rejects_invalid_protocol(self):
        """未知 action 和错误 arguments 类型继续返回原有协议错误。"""
        invalid_action, action_error = agent_protocol.parse_agent_action(
            '{"action":"wait"}'
        )
        invalid_args, args_error = agent_protocol.parse_agent_action(
            '{"action":"tool","tool":"calculator","arguments":[]}'
        )

        self.assertIsNone(invalid_action)
        self.assertEqual(action_error, "action must be tool or final")
        self.assertIsNone(invalid_args)
        self.assertEqual(args_error, "arguments must be an object")

    def test_parse_plan_keeps_step_normalization_and_limit(self):
        """planner 仍会清理目标、统一状态、截断标题并最多保留五步。"""
        long_title = "x" * 161
        raw_steps = [
            {"description": " first "},
            "second",
            {"title": long_title},
            {},
            "fifth",
            "sixth",
        ]

        result, error = agent_protocol.parse_plan(json.dumps({
            "goal": " goal ",
            "steps": raw_steps,
        }))

        self.assertIsNone(error)
        self.assertEqual(result["goal"], "goal")
        self.assertEqual(len(result["steps"]), 5)
        self.assertEqual(result["steps"][0]["title"], "first")
        self.assertEqual(result["steps"][2]["title"], f"{'x' * 157}...")
        self.assertEqual(result["steps"][3]["title"], "Step 4")
        self.assertTrue(all(step["status"] == "planned" for step in result["steps"]))
        self.assertEqual(result["current_step"], 1)

    def test_parse_plan_rejects_malformed_plan(self):
        """planner 缺少目标、步骤或返回额外字段时继续被拒绝。"""
        cases = (
            ('{"goal":"","steps":["one"]}', "goal must be a non-empty string"),
            ('{"goal":"g","steps":[]}', "steps must be a non-empty list"),
            ('{"goal":"g","steps":["one"],"extra":1}', "unexpected plan keys: extra"),
        )

        for text, expected_error in cases:
            with self.subTest(text=text):
                result, error = agent_protocol.parse_plan(text)
                self.assertIsNone(result)
                self.assertEqual(error, expected_error)

    def test_decision_and_planner_prompts_match_pre_migration_baseline(self):
        """三个已有 prompt 的完整输出哈希必须与迁移前基线一致。"""
        tool = PublicTool()
        prompts = (
            agent_protocol.build_tool_call_prompt("question", [tool]),
            agent_protocol.build_plan_prompt("question"),
            agent_protocol.build_multi_step_prompt(
                "question",
                [tool],
                [{"step": 1, "observation": "ok"}],
            ),
        )
        expected_hashes = (
            "c9c3307f9aaddb98874765ccf1d87c9494f68ed132c6478128a36153c5ac62d8",
            "ae35a3b3b96b84ba811480a18373344e92e40008e70a697e68fbf882101ba1eb",
            "44a54f47db2f78faddf5fc61cb03c430db9bac881b1c398f0b6cbe07753cd436",
        )

        self.assertEqual(
            tuple(hashlib.sha256(prompt.encode("utf-8")).hexdigest() for prompt in prompts),
            expected_hashes,
        )

    def test_final_answer_prompt_builders_keep_existing_layout(self):
        """单步和多步最终回答 prompt 仍保留原字段顺序与观察值格式。"""
        single = agent_protocol.build_final_answer_prompt("问题", "calculator", "结果")
        multi = agent_protocol.build_multi_step_final_answer_prompt(
            "问题",
            [{"step": 1, "observation": "结果"}],
        )

        self.assertIn("User question:\n问题\n\nSelected tool:\ncalculator", single)
        self.assertTrue(single.endswith("Tool observation:\n结果\n\nFinal answer:"))
        self.assertIn(
            'Agent steps and observations:\n[\n  {\n    "step": 1,\n    "observation": "结果"\n  }\n]',
            multi,
        )
        self.assertTrue(multi.endswith("Final answer:"))

    def test_agent_service_keeps_protocol_compatibility_exports(self):
        """旧调用方从 agent_service 导入协议名称时仍获得迁移后的同一对象。"""
        names = (
            "normalize_tool_spec",
            "build_tool_call_prompt",
            "extract_json_object",
            "parse_tool_call",
            "parse_agent_action",
            "normalize_plan_step",
            "parse_plan",
            "build_plan_prompt",
            "build_multi_step_prompt",
        )

        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(agent_service, name), getattr(agent_protocol, name))
        self.assertIs(agent_service.PLAN_STATUSES, agent_protocol.PLAN_STATUSES)


if __name__ == "__main__":
    unittest.main()
