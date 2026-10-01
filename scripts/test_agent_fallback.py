"""验证 Agent 确定性 fallback 拆分前后的路由与兼容接口。"""

import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import agent_fallback  # noqa: E402
import agent_service  # noqa: E402


def tool_specs(*names):
    """构造 fallback 只会读取名称的最小工具列表。"""
    return [{"name": name} for name in names]


class AgentFallbackTest(unittest.TestCase):
    """覆盖时间、搜索、知识库、多步和 planner 的确定性选择。"""

    def test_time_query_keeps_timezone_mapping(self):
        """时间查询仍应选择 current_time，并保留地区到时区的映射。"""
        result = agent_fallback.choose_tool_without_llm(
            "新西兰现在几点",
            tool_specs("current_time", "browser_search"),
        )

        self.assertEqual(result["tool"], "current_time")
        self.assertEqual(result["arguments"], {"timezone": "Pacific/Auckland"})
        self.assertEqual(
            agent_fallback.infer_timezone_from_query("北京 current time"),
            "Asia/Shanghai",
        )

    def test_web_search_routing_is_unchanged(self):
        """新闻和最新信息查询仍应优先走 browser_search。"""
        result = agent_fallback.choose_tool_without_llm(
            "今天 OpenAI 有什么最新新闻",
            tool_specs("current_time", "browser_search", "kb_search"),
        )

        self.assertEqual(result["tool"], "browser_search")
        self.assertEqual(result["arguments"]["max_results"], 3)

    def test_kb_routing_is_unchanged(self):
        """知识库查询仍应选择 kb_search 并原样传递 query。"""
        query = "总结知识库中的 Docker 文档"
        result = agent_fallback.choose_tool_without_llm(
            query,
            tool_specs("kb_search"),
        )

        self.assertEqual(result["tool"], "kb_search")
        self.assertEqual(result["arguments"], {"query": query})

    def test_general_query_without_matching_tool_returns_none(self):
        """没有可匹配工具的一般问题仍返回 none，而不是猜测工具。"""
        result = agent_fallback.choose_tool_without_llm(
            "请解释递归是什么",
            tool_specs("calculator", "current_time"),
        )

        self.assertEqual(
            result,
            {
                "tool": "none",
                "arguments": {},
                "reason": "No available tool is relevant.",
            },
        )

    def test_multi_step_fallback_avoids_reusing_tool(self):
        """多步 fallback 在工具已使用后仍应转为 final。"""
        result = agent_fallback.choose_multi_step_action_without_llm(
            "新西兰现在几点",
            tool_specs("current_time"),
            [{"tool_call": {"tool": "current_time"}}],
        )

        self.assertEqual(result["action"], "final")
        self.assertEqual(result["tool"], "none")

    def test_planner_fallback_shapes_are_unchanged(self):
        """算术与文件读取请求仍生成原有 planner fallback 结构。"""
        arithmetic = agent_fallback.generate_plan_without_llm("2 + 3")
        file_plan = agent_fallback.generate_plan_without_llm(
            "read backend/app.py and summarize"
        )

        self.assertEqual(arithmetic["steps"][0]["title"], "Compute the arithmetic result")
        self.assertEqual(len(arithmetic["steps"]), 1)
        self.assertEqual(
            [step["title"] for step in file_plan["steps"]],
            ["Read the requested project file", "Summarize the relevant information"],
        )

    def test_agent_service_keeps_fallback_compatibility_exports(self):
        """旧调用方继续从 agent_service 获得同一组 fallback 对象。"""
        self.assertIs(
            agent_service.choose_tool_without_llm,
            agent_fallback.choose_tool_without_llm,
        )
        self.assertIs(
            agent_service.choose_multi_step_action_without_llm,
            agent_fallback.choose_multi_step_action_without_llm,
        )
        self.assertIs(
            agent_service.generate_plan_without_llm,
            agent_fallback.generate_plan_without_llm,
        )


if __name__ == "__main__":
    unittest.main()
