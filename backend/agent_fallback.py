"""Agent 在 LLM 决策不可用时使用的确定性路由规则。"""

import re


URL_PATTERN = re.compile(r"https?://[^\s<>'\")\]]+", flags=re.IGNORECASE)

TIME_QUERY_TERMS = [
    "现在几点",
    "当前时间",
    "今天几号",
    "今天星期几",
    "几点了",
    "time now",
    "current date",
    "current time",
]
WEB_SEARCH_TERMS = [
    "latest",
    "current product price",
    "recent release",
    "news",
    "web",
    "internet",
    "search online",
    "搜索网页",
    "联网",
    "最新",
    "新闻",
    "最近发布",
    "公开更新",
    "当前事件",
]
KB_SEARCH_TERMS = [
    "knowledge base",
    "local knowledge",
    "uploaded document",
    "project document",
    "知识库",
    "本地文档",
    "上传材料",
    "上传文件",
]
TIMEZONE_MAPPINGS = [
    (["新西兰", "奥克兰", "auckland"], "Pacific/Auckland"),
    (["中国", "北京", "shanghai", "beijing"], "Asia/Shanghai"),
    (["utc"], "UTC"),
]


def query_contains_any(query, terms):
    """用稳定关键词判断用户请求是否命中某类工具意图。"""
    normalized = query.lower()
    return any(term in normalized for term in terms)


def infer_timezone_from_query(query):
    """从时间问题中提取项目支持的时区名称，供 current_time 补默认参数。"""
    normalized = query.lower()

    for aliases, timezone_name in TIMEZONE_MAPPINGS:
        if any(alias in normalized for alias in aliases):
            return timezone_name

    return None


def is_time_query(query):
    """判断请求是否应优先交给时间工具。"""
    normalized = query.lower()
    return (
        query_contains_any(query, TIME_QUERY_TERMS)
        or (
            any(word in normalized for word in ["time", "date", "utc", "now"])
            and not is_web_search_query(query)
        )
    )


def is_web_search_query(query):
    """判断请求是否明确需要联网搜索。"""
    return query_contains_any(query, WEB_SEARCH_TERMS)


def is_kb_query(query):
    """判断请求是否明确要求查询当前知识库。"""
    return query_contains_any(query, KB_SEARCH_TERMS)


def choose_tool_without_llm(query, available_tools):
    """在 LLM 决策不可用时，用确定性规则选择单步工具。

    规则只会选择本次允许的工具，并返回与模型解析结果相同的结构，使 Agent 后续
    执行流程无需区分结果来自 LLM 还是回退逻辑。
    """
    tool_names = {
        tool["name"]
        for tool in available_tools
    }
    normalized = query.lower()

    expression_match = re.search(
        r"(\d+(?:\s*[\+\-\*/%]\s*\d+)+)",
        query,
    )
    if "calculator" in tool_names and expression_match:
        return {
            "tool": "calculator",
            "arguments": {
                "expression": expression_match.group(1),
            },
            "reason": "The query contains an arithmetic expression.",
        }

    if "browser_search" in tool_names and is_web_search_query(query):
        return {
            "tool": "browser_search",
            "arguments": {
                "query": query,
                "max_results": 3,
            },
            "reason": "The query asks for current public web information.",
        }

    if "current_time" in tool_names and is_time_query(query):
        arguments = {}
        timezone_name = infer_timezone_from_query(query)

        if timezone_name:
            arguments["timezone"] = timezone_name

        return {
            "tool": "current_time",
            "arguments": arguments,
            "reason": "The query asks for current time or date.",
        }

    select_match = re.search(r"select\b.+", query, flags=re.IGNORECASE | re.DOTALL)
    sqlite_mcp_requested = "sqlite" in normalized and "mcp" in normalized

    if "mcp.sqlite.query" in tool_names and sqlite_mcp_requested:
        return {
            "tool": "mcp.sqlite.query",
            "arguments": {
                "sql": select_match.group(0).strip() if select_match else "SELECT COUNT(*) AS count FROM conversation",
            },
            "reason": "The query explicitly asks to use the SQLite MCP tool.",
        }

    if "sqlite_readonly_query" in tool_names:
        if select_match:
            return {
                "tool": "sqlite_readonly_query",
                "arguments": {
                    "sql": select_match.group(0).strip(),
                },
                "reason": "The query contains a read-only SQL SELECT statement.",
            }

        if any(word in normalized for word in ["sqlite", "database", "table", "conversation count"]):
            return {
                "tool": "sqlite_readonly_query",
                "arguments": {
                    "sql": "SELECT COUNT(*) AS count FROM conversation",
                },
                "reason": "The query asks to inspect SQLite database state.",
            }

    if "filesystem_readonly_read" in tool_names:
        path_match = re.search(
            r"([A-Za-z0-9_\-./]+\.(?:css|html|js|json|md|py|toml|ts|tsx|txt|ya?ml))",
            query,
            flags=re.IGNORECASE,
        )
        if path_match and any(word in normalized for word in ["read", "open", "inspect", "show", "查看", "读取"]):
            return {
                "tool": "filesystem_readonly_read",
                "arguments": {
                    "path": path_match.group(1),
                },
                "reason": "The query asks to read a project text file.",
            }

    if "mcp.filesystem.read_file" in tool_names:
        path_match = re.search(
            r"([A-Za-z0-9_\-./]+\.(?:css|html|js|json|md|py|toml|ts|tsx|txt|ya?ml))",
            query,
            flags=re.IGNORECASE,
        )
        if path_match and any(
            word in normalized
            for word in ["read", "open", "inspect", "show", "summarize", "summary", "查看", "读取"]
        ):
            return {
                "tool": "mcp.filesystem.read_file",
                "arguments": {
                    "path": path_match.group(1),
                },
                "reason": "The query asks to read a project text file through MCP.",
            }

    if "browser_read" in tool_names:
        url_match = URL_PATTERN.search(query)
        if url_match and any(
            word in normalized
            for word in [
                "read",
                "summarize",
                "summary",
                "inspect",
                "page",
                "url",
                "网页",
                "读取",
                "总结",
                "摘要",
            ]
        ):
            return {
                "tool": "browser_read",
                "arguments": {
                    "url": url_match.group(0).rstrip(".,;"),
                    "max_chars": 4000,
                },
                "reason": "The query provides a URL and asks to read its page content.",
            }

    if (
        "mcp.demo.echo" in tool_names
        and "mcp" in normalized
        and "echo" in normalized
    ):
        quoted = re.search(r"['\"]([^'\"]+)['\"]", query)
        message = quoted.group(1) if quoted else query
        return {
            "tool": "mcp.demo.echo",
            "arguments": {
                "message": message,
            },
            "reason": "The query explicitly asks to use the demo MCP echo tool.",
        }

    if "kb_search" in tool_names:
        reason = "The query can be answered by searching the knowledge base."
        if is_kb_query(query):
            reason = "The query asks about local knowledge base or uploaded content."

        return {
            "tool": "kb_search",
            "arguments": {
                "query": query,
            },
            "reason": reason,
        }

    return {
        "tool": "none",
        "arguments": {},
        "reason": "No available tool is relevant.",
    }


def choose_multi_step_action_without_llm(query, available_tools, steps):
    """根据已完成步骤确定下一次工具调用；没有待办工具时结束多步流程。"""
    used_tools = {
        (step.get("tool_call") or {}).get("tool")
        for step in steps
        if (step.get("tool_call") or {}).get("tool")
    }
    tool_call = choose_tool_without_llm(query, available_tools)

    if tool_call["tool"] != "none" and tool_call["tool"] not in used_tools:
        return {
            "action": "tool",
            **tool_call,
            "final_answer": None,
        }

    tool_names = {
        tool["name"]
        for tool in available_tools
    }
    normalized = query.lower()

    if (
        "current_time" in tool_names
        and "current_time" not in used_tools
        and is_time_query(query)
    ):
        arguments = {}
        timezone_name = infer_timezone_from_query(query)

        if timezone_name:
            arguments["timezone"] = timezone_name

        return {
            "action": "tool",
            "tool": "current_time",
            "arguments": arguments,
            "reason": "The query also asks for current time or date.",
            "final_answer": None,
        }

    return {
        "action": "final",
        "tool": "none",
        "arguments": {},
        "reason": "Enough observations are available to answer.",
        "final_answer": None,
    }


def generate_plan_without_llm(query):
    """在 Planner 模型失败时，根据可识别意图生成最小可执行计划。"""
    normalized = query.lower()

    if re.search(r"\d+\s*[\+\-\*/%]\s*\d+", query):
        return {
            "goal": f"Answer: {query}",
            "steps": [
                {
                    "id": 1,
                    "title": "Compute the arithmetic result",
                    "status": "planned",
                }
            ],
            "status": "planned",
            "current_step": 1,
            "observations": [],
        }

    if (
        re.search(
            r"([A-Za-z0-9_\-./]+\.(?:css|html|js|json|md|py|toml|ts|tsx|txt|ya?ml))",
            query,
            flags=re.IGNORECASE,
        )
        and any(word in normalized for word in ["read", "open", "inspect", "show", "summarize", "summary"])
    ):
        return {
            "goal": query.strip(),
            "steps": [
                {
                    "id": 1,
                    "title": "Read the requested project file",
                    "status": "planned",
                },
                {
                    "id": 2,
                    "title": "Summarize the relevant information",
                    "status": "planned",
                },
            ],
            "status": "planned",
            "current_step": 1,
            "observations": [],
        }

    return {
        "goal": query.strip(),
        "steps": [
            {
                "id": 1,
                "title": "Understand the request",
                "status": "planned",
            },
            {
                "id": 2,
                "title": "Use available tools if needed",
                "status": "planned",
            },
            {
                "id": 3,
                "title": "Write the final answer",
                "status": "planned",
            },
        ],
        "status": "planned",
        "current_step": 1,
        "observations": [],
    }
