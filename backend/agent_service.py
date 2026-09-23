import json
import re

from db import (
    create_conversation,
    get_conversation,
    get_conversation_messages,
    save_message,
)
from model_config import (
    get_default_chat_model,
    get_default_temperature,
    get_openai_client,
)
from services.tools import list_all_tools, list_tools, resolve_tool, run_tool


ALLOWED_TOOL_KEYS = {"tool", "arguments", "reason"}
ALLOWED_AGENT_ACTION_KEYS = {
    "action",
    "tool",
    "arguments",
    "reason",
    "final_answer",
}
ALLOWED_PLAN_KEYS = {"goal", "steps"}
ALLOWED_PLAN_STEP_KEYS = {"id", "title", "status"}
PLAN_STATUSES = {"planned", "running", "completed", "failed", "skipped"}
MAX_AGENT_STEPS = 5
OBSERVATION_MAX_CHARS = 1800
STREAM_VALUE_MAX_CHARS = 1200
URL_PATTERN = re.compile(r"https?://[^\s<>'\")\]]+", flags=re.IGNORECASE)
STREAM_REDACTED_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "command",
    "cwd",
    "env",
    "environment",
    "stderr",
}

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
    """负责 query_contains_any 的函数职责。"""
    normalized = query.lower()
    return any(term in normalized for term in terms)


def infer_timezone_from_query(query):
    """负责 infer_timezone_from_query 的函数职责。"""
    normalized = query.lower()

    for aliases, timezone_name in TIMEZONE_MAPPINGS:
        if any(alias in normalized for alias in aliases):
            return timezone_name

    return None


def is_time_query(query):
    """负责 is_time_query 的函数职责。"""
    normalized = query.lower()
    return (
        query_contains_any(query, TIME_QUERY_TERMS)
        or (
            any(word in normalized for word in ["time", "date", "utc", "now"])
            and not is_web_search_query(query)
        )
    )


def is_web_search_query(query):
    """负责 is_web_search_query 的函数职责。"""
    return query_contains_any(query, WEB_SEARCH_TERMS)


def is_kb_query(query):
    """负责 is_kb_query 的函数职责。"""
    return query_contains_any(query, KB_SEARCH_TERMS)


def normalize_tool_spec(tool):
    """负责 normalize_tool_spec 的函数职责。"""
    if hasattr(tool, "public_dict"):
        return tool.public_dict()

    return tool


def get_available_tool_specs(tool_names=None):
    # 显式指定本地工具时无需探测 MCP，避免无关的 MCP 冷启动拖慢 Agent。
    """负责 get_available_tool_specs 的函数职责。"""
    if tool_names is not None and all(
        not str(name).startswith("mcp.") for name in tool_names
    ):
        registry = {
            tool["name"]: tool
            for tool in list_tools()
        }
    else:
        registry = {
            tool["name"]: tool
            for tool in list_all_tools()
        }

    if tool_names is None:
        return list(registry.values()), None

    missing = [
        name
        for name in tool_names
        if name not in registry
    ]

    if missing:
        return None, f"unknown tools: {', '.join(missing)}"

    return [
        registry[name]
        for name in tool_names
    ], None


def build_tool_call_prompt(query, available_tools):
    """负责 build_tool_call_prompt 的函数职责。"""
    tool_names = [
        normalize_tool_spec(tool)["name"]
        for tool in available_tools
    ]
    tool_choices = " | ".join([*tool_names, "none"])
    tools_text = json.dumps(
        [normalize_tool_spec(tool) for tool in available_tools],
        ensure_ascii=False,
        indent=2,
    )

    return f"""
You are a tool selection router for Mini ChatChat.

Choose exactly one tool for the user query, or choose "none" if no tool is needed.

Available tools:
{tools_text}

User query:
{query}

Return only valid JSON. Do not use markdown. Do not explain outside JSON.

Required JSON shape:
{{
  "tool": "{tool_choices}",
  "arguments": {{}},
  "reason": "short reason"
}}

Rules:
- Use calculator for arithmetic expressions.
- Use current_time for clock/date questions such as "现在几点", "当前时间", "今天几号", "今天星期几", "time now", "current date", or timezone-specific time questions.
- For "新西兰", "奥克兰", or "Auckland" time questions, call current_time with {{"timezone": "Pacific/Auckland"}}.
- For "中国", "北京", "Shanghai", or "Beijing" time questions, call current_time with {{"timezone": "Asia/Shanghai"}}.
- For UTC time questions, call current_time with {{"timezone": "UTC"}}.
- Use browser_search for latest news, public web updates, current product prices, recently released information, current events, or explicit web search requests.
- Use kb_search for questions about the local knowledge base, project documents, uploaded materials, or user-provided KB content.
- Use sqlite_readonly_query for read-only SQL SELECT questions about Mini ChatChat database tables.
- Use filesystem_readonly_read for read-only questions that ask to inspect a project file by relative path.
- Use browser_read when the user provides a direct public http or https URL and asks to read, summarize, inspect, or answer from that page.
- Do not use current_time for news/current-event questions; use browser_search instead.
- Use mcp.demo.echo only when the user explicitly asks to echo through the demo MCP tool.
- Use mcp.filesystem.read_file for read-only project file inspection through MCP.
- Use mcp.sqlite.query when the user explicitly asks for the SQLite MCP tool.
- Do not choose browser_search when the user already supplied the exact URL to read.
- Use none when no available tool is relevant.
- Only choose a tool listed in Available tools, or "none".
""".strip()


def extract_json_object(text):
    """负责 extract_json_object 的函数职责。"""
    stripped = (text or "").strip()

    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()

    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match:
        return match.group(0)

    return stripped


def parse_tool_call(llm_text):
    """负责 parse_tool_call 的函数职责。"""
    try:
        data = json.loads(extract_json_object(llm_text))
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON tool call: {exc}"

    if not isinstance(data, dict):
        return None, "tool call must be a JSON object"

    extra_keys = set(data) - ALLOWED_TOOL_KEYS
    if extra_keys:
        return None, f"unexpected tool call keys: {', '.join(sorted(extra_keys))}"

    tool_name = data.get("tool")
    if not isinstance(tool_name, str) or not tool_name:
        return None, "tool must be a non-empty string"

    arguments = data.get("arguments", {})
    if not isinstance(arguments, dict):
        return None, "arguments must be an object"

    reason = data.get("reason", "")
    if not isinstance(reason, str):
        return None, "reason must be a string"

    return {
        "tool": tool_name,
        "arguments": arguments,
        "reason": reason,
    }, None


def parse_agent_action(llm_text):
    """负责 parse_agent_action 的函数职责。"""
    try:
        data = json.loads(extract_json_object(llm_text))
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON agent action: {exc}"

    if not isinstance(data, dict):
        return None, "agent action must be a JSON object"

    extra_keys = set(data) - ALLOWED_AGENT_ACTION_KEYS
    if extra_keys:
        return None, f"unexpected agent action keys: {', '.join(sorted(extra_keys))}"

    action = data.get("action")
    if action not in {"tool", "final"}:
        return None, "action must be tool or final"

    final_answer = data.get("final_answer")
    if final_answer is not None and not isinstance(final_answer, str):
        return None, "final_answer must be a string or null"

    tool_name = data.get("tool", "none")
    if not isinstance(tool_name, str) or not tool_name:
        return None, "tool must be a non-empty string"

    arguments = data.get("arguments", {})
    if not isinstance(arguments, dict):
        return None, "arguments must be an object"

    reason = data.get("reason", "")
    if not isinstance(reason, str):
        return None, "reason must be a string"

    if action == "final":
        tool_name = "none"
        arguments = {}

    return {
        "action": action,
        "tool": tool_name,
        "arguments": arguments,
        "reason": reason,
        "final_answer": final_answer,
    }, None


def normalize_plan_step(step, index):
    """负责 normalize_plan_step 的函数职责。"""
    title = ""
    if isinstance(step, dict):
        title = step.get("title") or step.get("description") or ""
    elif isinstance(step, str):
        title = step

    title = str(title).strip() or f"Step {index}"
    if len(title) > 160:
        title = f"{title[:157]}..."

    return {
        "id": index,
        "title": title,
        "status": "planned",
    }


def parse_plan(llm_text):
    """负责 parse_plan 的函数职责。"""
    try:
        data = json.loads(extract_json_object(llm_text))
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON plan: {exc}"

    if not isinstance(data, dict):
        return None, "plan must be a JSON object"

    extra_keys = set(data) - ALLOWED_PLAN_KEYS
    if extra_keys:
        return None, f"unexpected plan keys: {', '.join(sorted(extra_keys))}"

    goal = data.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        return None, "goal must be a non-empty string"

    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        return None, "steps must be a non-empty list"

    steps = [
        normalize_plan_step(step, index + 1)
        for index, step in enumerate(raw_steps[:5])
    ]

    return {
        "goal": goal.strip(),
        "steps": steps,
        "status": "planned",
        "current_step": steps[0]["id"] if steps else None,
        "observations": [],
    }, None


def choose_tool_without_llm(query, available_tools):
    """负责 choose_tool_without_llm 的函数职责。"""
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
    """负责 choose_multi_step_action_without_llm 的函数职责。"""
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
    """负责 generate_plan_without_llm 的函数职责。"""
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


def build_plan_prompt(query):
    """负责 build_plan_prompt 的函数职责。"""
    return f"""
You are Mini ChatChat's lightweight planner.

Create a short execution plan for the user request. The planner does not call
tools. It only describes what should happen.

User request:
{query}

Return only valid JSON. Do not use markdown. Do not explain outside JSON.

Required JSON shape:
{{
  "goal": "short goal",
  "steps": [
    {{
      "id": 1,
      "title": "short step title"
    }}
  ]
}}

Rules:
- Generate 2 to 5 steps when the task needs reading, tool use, or synthesis.
- Generate 1 step for very simple questions such as arithmetic.
- Do not generate more than 5 steps.
- Do not call tools.
- Each step title must be concrete and concise.
""".strip()


def generate_plan(query):
    """负责 generate_plan 的函数职责。"""
    fallback = generate_plan_without_llm(query)
    prompt = build_plan_prompt(query)

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=get_default_chat_model(),
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        raw_output = response.choices[0].message.content or ""
    except Exception:
        return fallback

    plan, error = parse_plan(raw_output)
    if error:
        return fallback

    return plan


def decide_tool_call(query, available_tools):
    """负责 decide_tool_call 的函数职责。"""
    prompt = build_tool_call_prompt(query, available_tools)
    fallback = choose_tool_without_llm(query, available_tools)

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=get_default_chat_model(),
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        raw_output = response.choices[0].message.content or ""
    except Exception as exc:
        raw_output = json.dumps(fallback, ensure_ascii=False)
        return {
            "tool_call": fallback,
            "raw_model_output": raw_output,
            "error": f"LLM tool decision failed, used deterministic fallback: {exc}",
        }

    tool_call, error = parse_tool_call(raw_output)
    if error:
        return {
            "tool_call": None,
            "raw_model_output": raw_output,
            "error": error,
        }

    if (
        fallback.get("tool") == "mcp.sqlite.query"
        and tool_call.get("tool") == "sqlite_readonly_query"
    ):
        return {
            "tool_call": fallback,
            "raw_model_output": raw_output,
            "error": None,
        }

    if (
        tool_call.get("tool") == "none"
        and fallback.get("tool") != "none"
        and len(available_tools) == 1
    ):
        return {
            "tool_call": fallback,
            "raw_model_output": raw_output,
            "error": None,
        }

    return {
        "tool_call": tool_call,
        "raw_model_output": raw_output,
        "error": None,
    }


def build_multi_step_prompt(query, available_tools, steps):
    """负责 build_multi_step_prompt 的函数职责。"""
    tool_names = [
        normalize_tool_spec(tool)["name"]
        for tool in available_tools
    ]
    tool_choices = " | ".join([*tool_names, "none"])
    tools_text = json.dumps(
        [normalize_tool_spec(tool) for tool in available_tools],
        ensure_ascii=False,
        indent=2,
    )
    steps_text = json.dumps(
        steps,
        ensure_ascii=False,
        indent=2,
    )

    return f"""
You are Mini ChatChat's multi-step agent controller.

Decide the next step for the user query. Use at most one tool in this step.
If enough observations are available, return action "final".

Available tools:
{tools_text}

User query:
{query}

Previous steps and observations:
{steps_text}

Return only valid JSON. Do not use markdown. Do not explain outside JSON.

Required JSON shape:
{{
  "action": "tool | final",
  "tool": "{tool_choices}",
  "arguments": {{}},
  "reason": "short reason",
  "final_answer": null
}}

Rules:
- Use calculator for arithmetic expressions.
- Use current_time for clock/date questions such as "现在几点", "当前时间", "今天几号", "今天星期几", "time now", "current date", or timezone-specific time questions.
- For "新西兰", "奥克兰", or "Auckland" time questions, call current_time with {{"timezone": "Pacific/Auckland"}}.
- For "中国", "北京", "Shanghai", or "Beijing" time questions, call current_time with {{"timezone": "Asia/Shanghai"}}.
- For UTC time questions, call current_time with {{"timezone": "UTC"}}.
- Use browser_search for latest news, public web updates, current product prices, recently released information, current events, or explicit web search.
- Use kb_search for questions about the local knowledge base, project documents, uploaded materials, or user-provided KB content.
- Use sqlite_readonly_query only for read-only SELECT database questions.
- Use filesystem_readonly_read only for read-only project file inspection.
- Use browser_read when the user provides a direct public URL to read.
- Do not use current_time for news/current-event questions; use browser_search instead.
- Use mcp.demo.echo only when the user explicitly asks to echo through the demo MCP tool.
- Use mcp.filesystem.read_file for read-only project file inspection through MCP.
- Use mcp.sqlite.query when the user explicitly asks for the SQLite MCP tool.
- Do not repeat the same tool with the same arguments.
- Use final when tool observations are sufficient or no allowed tool is useful.
- Only choose a tool listed in Available tools, or "none".
""".strip()


def decide_agent_action(query, available_tools, steps):
    # Agent 每轮只允许一个工具调用；模型不可用或输出非法时回退到确定性路由。
    """负责 decide_agent_action 的函数职责。"""
    prompt = build_multi_step_prompt(query, available_tools, steps)
    fallback = choose_multi_step_action_without_llm(query, available_tools, steps)

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=get_default_chat_model(),
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        raw_output = response.choices[0].message.content or ""
    except Exception as exc:
        raw_output = json.dumps(fallback, ensure_ascii=False)
        return {
            "action": fallback,
            "raw_model_output": raw_output,
            "error": f"LLM agent decision failed, used deterministic fallback: {exc}",
        }

    action, error = parse_agent_action(raw_output)
    if error:
        return {
            "action": fallback,
            "raw_model_output": raw_output,
            "error": error,
        }

    if (
        fallback.get("action") == "tool"
        and fallback.get("tool") == "mcp.sqlite.query"
        and action.get("action") == "tool"
        and action.get("tool") == "sqlite_readonly_query"
    ):
        return {
            "action": fallback,
            "raw_model_output": raw_output,
            "error": None,
        }

    if (
        action.get("action") == "final"
        and fallback.get("action") == "tool"
    ):
        return {
            "action": fallback,
            "raw_model_output": raw_output,
            "error": None,
        }

    used_tools = {
        (step.get("tool_call") or {}).get("tool")
        for step in steps
        if (step.get("tool_call") or {}).get("tool")
    }
    if (
        action.get("action") == "tool"
        and action.get("tool") in used_tools
        and fallback.get("action") == "final"
    ):
        return {
            "action": fallback,
            "raw_model_output": raw_output,
            "error": None,
        }

    return {
        "action": action,
        "raw_model_output": raw_output,
        "error": None,
    }


def apply_tool_defaults(tool_call, query, kb_name, user_id=None):
    """负责 apply_tool_defaults 的函数职责。"""
    if tool_call["tool"] == "kb_search":
        arguments = {
            **tool_call.get("arguments", {}),
        }
        arguments.setdefault("query", query)

        if kb_name:
            arguments.setdefault("kb_name", kb_name)

        if user_id is not None:
            arguments["_user_id"] = user_id

        tool_call = {
            **tool_call,
            "arguments": arguments,
        }

    if tool_call["tool"] == "current_time":
        arguments = {
            **tool_call.get("arguments", {}),
        }
        timezone_name = infer_timezone_from_query(query)

        if timezone_name:
            arguments.setdefault("timezone", timezone_name)

        tool_call = {
            **tool_call,
            "arguments": arguments,
        }

    return tool_call


def expand_explicit_mcp_tools(query, tools):
    """负责 expand_explicit_mcp_tools 的函数职责。"""
    if tools is None:
        return None

    normalized = query.lower()
    expanded = list(tools)

    if (
        "sqlite" in normalized
        and "mcp" in normalized
        and "mcp.sqlite.query" not in expanded
    ):
        expanded.append("mcp.sqlite.query")

    return expanded


def get_tool_trace_metadata(tool_name):
    """负责 get_tool_trace_metadata 的函数职责。"""
    spec = resolve_tool(tool_name)
    if spec is None or getattr(spec, "provider", "local") != "mcp":
        return {}

    return {
        "provider": "mcp",
        "server": getattr(spec, "server_name", None),
        "tool": getattr(spec, "tool_name", None),
    }


def run_agent_once(query, kb_name=None, tools=None, user_id=None):
    """负责 run_agent_once 的函数职责。"""
    tools = expand_explicit_mcp_tools(query, tools)
    available_tools, tools_error = get_available_tool_specs(tools)
    if tools_error:
        return {
            "tool_call": None,
            "tool_result": None,
            "trace": [
                {
                    "type": "error",
                    "message": tools_error,
                }
            ],
            "error": tools_error,
        }

    decision = decide_tool_call(query, available_tools)
    tool_call = decision.get("tool_call")
    trace = [
        {
            "type": "tool_decision",
            "tool_call": tool_call,
            "raw_model_output": decision.get("raw_model_output"),
            "error": decision.get("error"),
        }
    ]

    if decision.get("error") and not tool_call:
        return {
            "tool_call": None,
            "tool_result": None,
            "trace": trace,
            "error": decision["error"],
        }

    tool_call = apply_tool_defaults(tool_call, query, kb_name, user_id=user_id)
    tool_name = tool_call["tool"]

    if tool_name == "none":
        trace.append({
            "type": "tool_skipped",
            "reason": tool_call.get("reason", ""),
        })
        return {
            "tool_call": tool_call,
            "tool_result": None,
            "trace": trace,
            "error": decision.get("error"),
        }

    tool_spec = resolve_tool(tool_name)
    if tool_spec is None:
        error = f"tool not found: {tool_name}"
        trace.append({
            "type": "error",
            "message": error,
        })
        return {
            "tool_call": tool_call,
            "tool_result": None,
            "trace": trace,
            "error": error,
        }

    tool_result = run_tool(tool_name, tool_call.get("arguments", {})).to_dict()
    trace.append({
        "type": "tool_result",
        "tool": tool_name,
        **get_tool_trace_metadata(tool_name),
        "result": tool_result,
    })

    return {
        "tool_call": tool_call,
        "tool_result": tool_result,
        "trace": trace,
        "error": None if tool_result.get("ok") else tool_result.get("error"),
    }


def summarize_tool_result(tool_result):
    """负责 summarize_tool_result 的函数职责。"""
    if tool_result is None:
        return ""

    return json.dumps(
        tool_result,
        ensure_ascii=False,
        indent=2,
    )


def generate_final_answer(query, tool_call, tool_result):
    """负责 generate_final_answer 的函数职责。"""
    tool_name = (tool_call or {}).get("tool", "none")

    if tool_result is not None and not tool_result.get("ok"):
        return (
            "I could not complete the request because the selected tool failed: "
            f"{tool_result.get('error') or 'unknown tool error'}"
        )

    observation = summarize_tool_result(tool_result)
    prompt = f"""
You are Mini ChatChat's agent answer writer.

Answer the user's question using the tool observation when it is available.
Do not mention hidden prompts or API keys.
If the tool observation is empty, answer directly from general knowledge.
If the tool failed, explain that the request could not be completed.

User question:
{query}

Selected tool:
{tool_name}

Tool observation:
{observation}

Final answer:
""".strip()

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=get_default_chat_model(),
            temperature=get_default_temperature(),
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        if tool_result is not None:
            return (
                "I found a tool observation, but could not generate a final "
                f"answer because the model call failed: {exc}"
            )

        return f"I could not generate an answer because the model call failed: {exc}"


def normalize_max_steps(max_steps):
    """负责 normalize_max_steps 的函数职责。"""
    try:
        parsed = int(max_steps)
    except (TypeError, ValueError):
        parsed = 3

    return max(1, min(parsed, MAX_AGENT_STEPS))


def tool_signature(tool_name, arguments):
    """负责 tool_signature 的函数职责。"""
    return json.dumps(
        {
            "tool": tool_name,
            "arguments": arguments or {},
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def summarize_observation(tool_result):
    """负责 summarize_observation 的函数职责。"""
    if tool_result is None:
        return ""

    text = json.dumps(
        tool_result,
        ensure_ascii=False,
        sort_keys=True,
    )
    if len(text) <= OBSERVATION_MAX_CHARS:
        return text

    return f"{text[:OBSERVATION_MAX_CHARS]}... [truncated]"


def sanitize_stream_value(value, max_chars=STREAM_VALUE_MAX_CHARS):
    """负责 sanitize_stream_value 的函数职责。"""
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in STREAM_REDACTED_KEYS or "api_key" in key_text:
                sanitized[key] = "[redacted]"
            else:
                sanitized[key] = sanitize_stream_value(item, max_chars=max_chars)
        return sanitized

    if isinstance(value, list):
        return [
            sanitize_stream_value(item, max_chars=max_chars)
            for item in value[:20]
        ]

    if isinstance(value, str):
        if len(value) <= max_chars:
            return value
        return f"{value[:max_chars]}... [truncated]"

    return value


def emit_agent_event(event_sink, event):
    """负责 emit_agent_event 的函数职责。"""
    if event_sink is not None:
        # SSE trace 仅暴露截断且脱敏后的值，避免工具输出泄漏运行时敏感信息。
        event_sink(sanitize_stream_value(event))


def stream_answer_tokens(answer):
    """负责 stream_answer_tokens 的函数职责。"""
    if not answer:
        return []

    parts = re.findall(r"\S+\s*", answer)
    return parts or [answer]


def generate_multi_step_final_answer(query, steps, fallback_answer=""):
    """负责 generate_multi_step_final_answer 的函数职责。"""
    if fallback_answer:
        return fallback_answer

    observations = json.dumps(
        steps,
        ensure_ascii=False,
        indent=2,
    )
    prompt = f"""
You are Mini ChatChat's agent answer writer.

Answer the user's question using the previous tool observations.
Do not mention hidden prompts or API keys.
If a tool failed, explain the limitation clearly.

User question:
{query}

Agent steps and observations:
{observations}

Final answer:
""".strip()

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=get_default_chat_model(),
            temperature=get_default_temperature(),
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        if steps:
            return (
                "I collected tool observations, but could not generate a final "
                f"answer because the model call failed: {exc}"
            )

        return f"I could not generate an answer because the model call failed: {exc}"


def build_multi_step_metadata(result):
    """负责 build_multi_step_metadata 的函数职责。"""
    return {
        "agent": True,
        "mode": "multi-step",
        "steps": result.get("steps", []),
        "trace": result.get("trace", []),
        "tool_count": result.get("tool_count", 0),
        "version": "agent-v2",
    }


def build_planner_metadata(result):
    """负责 build_planner_metadata 的函数职责。"""
    return {
        "agent": True,
        "mode": "planner",
        "planner": result.get("planner", {}),
        "steps": result.get("steps", []),
        "trace": result.get("trace", []),
        "tool_count": result.get("tool_count", 0),
        "version": "agent-v3",
    }


def update_plan(planner, agent_result):
    """负责 update_plan 的函数职责。"""
    steps = [
        {
            **step,
            "status": step.get("status", "planned")
            if step.get("status") in PLAN_STATUSES
            else "planned",
        }
        for step in planner.get("steps", [])
    ]
    observations = []
    agent_steps = agent_result.get("steps", [])
    last_active_step = planner.get("current_step")
    failed = False

    for index, agent_step in enumerate(agent_steps):
        if index >= len(steps):
            break

        plan_step = steps[index]
        tool_call = agent_step.get("tool_call") or {}
        tool_result = agent_step.get("tool_result") or {}
        ok = bool(tool_result.get("ok"))
        status = "completed" if ok else "failed"
        summary = agent_step.get("observation") or summarize_observation(tool_result)

        plan_step["status"] = status
        plan_step["observation"] = summary
        observations.append({
            "step": plan_step.get("id"),
            "tool": tool_call.get("tool"),
            "ok": ok,
            "summary": summary,
        })
        last_active_step = plan_step.get("id")

        if not ok:
            failed = True

    if failed:
        for plan_step in steps:
            if plan_step.get("status") == "planned":
                plan_step["status"] = "skipped"
        status = "failed"
    elif agent_result.get("answer"):
        first_remaining_completed = False
        for plan_step in steps:
            if plan_step.get("status") == "planned":
                if not first_remaining_completed:
                    plan_step["status"] = "completed"
                    plan_step["observation"] = "Final answer generated."
                    observations.append({
                        "step": plan_step.get("id"),
                        "tool": "final_answer",
                        "ok": True,
                        "summary": "Final answer generated.",
                    })
                    last_active_step = plan_step.get("id")
                    first_remaining_completed = True
                else:
                    plan_step["status"] = "skipped"
        status = "completed"
    else:
        for plan_step in steps:
            if plan_step.get("status") == "planned":
                plan_step["status"] = "skipped"
        status = "failed"

    return {
        "goal": planner.get("goal", ""),
        "steps": steps,
        "status": status,
        "current_step": last_active_step,
        "observations": observations,
    }


def run_agent_multi_step(
    query,
    kb_name=None,
    tools=None,
    max_steps=3,
    event_sink=None,
    should_stop=None,
    user_id=None,
):
    """负责 run_agent_multi_step 的函数职责。"""
    max_steps = normalize_max_steps(max_steps)
    tools = expand_explicit_mcp_tools(query, tools)
    available_tools, tools_error = get_available_tool_specs(tools)
    if tools_error:
        return {
            "answer": "",
            "steps": [],
            "trace": [
                {
                    "event": "error",
                    "message": tools_error,
                }
            ],
            "tool_count": 0,
            "error": tools_error,
        }

    allowed_tool_names = {
        normalize_tool_spec(tool)["name"]
        for tool in available_tools
    }
    steps = []
    trace = []
    seen_signatures = set()
    previous_signature = None
    final_answer = ""
    error = None
    stopped = False

    for step_index in range(1, max_steps + 1):
        if should_stop is not None and should_stop():
            error = "client disconnected"
            stopped = True
            trace.append({
                "step": step_index,
                "event": "error",
                "message": error,
            })
            break

        emit_agent_event(event_sink, {
            "type": "step_start",
            "step": step_index,
        })
        decision = decide_agent_action(query, available_tools, steps)
        action = decision.get("action")

        # 决策 LLM 可能在等待期间遇到断连；结果返回后不再启动新的工具阶段。
        if should_stop is not None and should_stop():
            error = "client disconnected"
            stopped = True
            trace.append({
                "step": step_index,
                "event": "error",
                "message": error,
            })
            break

        if decision.get("error"):
            trace.append({
                "step": step_index,
                "event": "decision_warning",
                "message": decision["error"],
            })

        if action is None:
            error = "agent decision missing"
            trace.append({
                "step": step_index,
                "event": "error",
                "message": error,
            })
            break

        if action["action"] == "final":
            final_answer = action.get("final_answer") or ""
            trace.append({
                "step": step_index,
                "event": "final_decision",
                "reason": action.get("reason", ""),
            })
            break

        tool_call = {
            "tool": action["tool"],
            "arguments": action.get("arguments", {}),
            "reason": action.get("reason", ""),
        }
        tool_call = apply_tool_defaults(tool_call, query, kb_name, user_id=user_id)
        tool_name = tool_call["tool"]
        arguments = tool_call.get("arguments", {})

        trace.append({
            "step": step_index,
            "event": "tool_decision",
            "tool": tool_name,
            **get_tool_trace_metadata(tool_name),
            "arguments": arguments,
            "reason": tool_call.get("reason", ""),
        })
        emit_agent_event(event_sink, {
            "type": "tool_call",
            "step": step_index,
            "tool_call": tool_call,
            **get_tool_trace_metadata(tool_name),
        })

        if tool_name == "none":
            final_answer = action.get("final_answer") or ""
            trace.append({
                "step": step_index,
                "event": "final_decision",
                "reason": tool_call.get("reason", ""),
            })
            break

        if tool_name not in allowed_tool_names or resolve_tool(tool_name) is None:
            tool_error = f"tool not allowed or not found: {tool_name}"
            tool_result = {
                "ok": False,
                "result": None,
                "error": tool_error,
                "metadata": {},
            }
            error = tool_error
        else:
            signature = tool_signature(tool_name, arguments)
            if signature == previous_signature:
                tool_result = {
                    "ok": False,
                    "result": None,
                    "error": "blocked repeated tool call with identical arguments",
                    "metadata": {
                        "loop_guard": "consecutive_repeat",
                    },
                }
                error = tool_result["error"]
            elif signature in seen_signatures:
                tool_result = {
                    "ok": False,
                    "result": None,
                    "error": "blocked tool loop with previously used arguments",
                    "metadata": {
                        "loop_guard": "seen_signature",
                    },
                }
                error = tool_result["error"]
            else:
                seen_signatures.add(signature)
                previous_signature = signature
                tool_result = run_tool(tool_name, arguments).to_dict()
                error = None if tool_result.get("ok") else tool_result.get("error")

        observation = summarize_observation(tool_result)
        step = {
            "step": step_index,
            "tool_call": tool_call,
            "tool_result": tool_result,
            "observation": observation,
        }
        steps.append(step)
        trace.append({
            "step": step_index,
            "event": "tool_result",
            "tool": tool_name,
            **get_tool_trace_metadata(tool_name),
            "ok": bool(tool_result.get("ok")),
            "summary": observation,
        })
        emit_agent_event(event_sink, {
            "type": "tool_result",
            "step": step_index,
            "tool": tool_name,
            **get_tool_trace_metadata(tool_name),
            "tool_result": tool_result,
            "observation": observation,
        })

    else:
        trace.append({
            "event": "max_steps_reached",
            "max_steps": max_steps,
        })

    # 客户端取消后不能再发起最终 LLM 总结；已在途调用无法由 SDK 强制撤销。
    answer = "" if stopped else generate_multi_step_final_answer(
        query,
        steps,
        final_answer,
    )
    trace.append({
        "event": "final_answer",
        "answer": answer,
    })

    tool_count = sum(
        1
        for step in steps
        if (step.get("tool_call") or {}).get("tool") != "none"
    )

    return {
        "answer": answer,
        "steps": steps,
        "trace": trace,
        "tool_count": tool_count,
        "error": error if error and not answer else None,
    }


def run_agent_with_planner(
    query,
    kb_name=None,
    tools=None,
    max_steps=3,
    event_sink=None,
    should_stop=None,
    user_id=None,
):
    """负责 run_agent_with_planner 的函数职责。"""
    planner = generate_plan(query)
    trace = [
        {
            "event": "plan_generated",
            "goal": planner.get("goal", ""),
            "step_count": len(planner.get("steps", [])),
        }
    ]
    emit_agent_event(event_sink, {
        "type": "planning",
        "planner": planner,
    })
    if should_stop is not None and should_stop():
        return {
            "answer": "",
            "steps": [],
            "trace": trace,
            "tool_count": 0,
            "error": "client disconnected",
            "planner": planner,
        }

    agent_result = run_agent_multi_step(
        query,
        kb_name=kb_name,
        tools=tools,
        max_steps=max_steps,
        event_sink=event_sink,
        should_stop=should_stop,
        user_id=user_id,
    )
    planner = update_plan(planner, agent_result)
    emit_agent_event(event_sink, {
        "type": "planner_update",
        "planner": planner,
    })
    trace.extend(agent_result.get("trace", []))
    trace.append({
        "event": "plan_updated",
        "status": planner.get("status"),
        "current_step": planner.get("current_step"),
    })

    result = {
        **agent_result,
        "planner": planner,
        "trace": trace,
    }
    for token in stream_answer_tokens(result.get("answer", "")):
        if should_stop is not None and should_stop():
            break
        emit_agent_event(event_sink, {
            "type": "token",
            "content": token,
        })

    return result


def run_agent(query, kb_name=None, tools=None, user_id=None):
    """负责 run_agent 的函数职责。"""
    run_once_result = run_agent_once(
        query,
        kb_name=kb_name,
        tools=tools,
        user_id=user_id,
    )
    trace = [
        {
            "type": item.get("type"),
            "tool": item.get("tool"),
            "tool_call": item.get("tool_call"),
            "error": item.get("error") or item.get("message"),
            "reason": item.get("reason"),
        }
        for item in run_once_result.get("trace", [])
    ]
    tool_call = run_once_result.get("tool_call")
    tool_result = run_once_result.get("tool_result")
    error = run_once_result.get("error")

    if error and not tool_call:
        return {
            "answer": "",
            "tool_call": tool_call,
            "tool_result": tool_result,
            "trace": trace,
            "error": error,
        }

    answer = generate_final_answer(
        query,
        tool_call,
        tool_result,
    )
    trace.append({
        "type": "final_answer",
    })

    return {
        "answer": answer,
        "tool_call": tool_call,
        "tool_result": tool_result,
        "trace": trace,
        "error": error if tool_result and not tool_result.get("ok") else None,
    }


def build_agent_metadata(tool_call, tool_result, trace):
    """负责 build_agent_metadata 的函数职责。"""
    tool_count = 0
    if tool_call and tool_call.get("tool") != "none" and tool_result is not None:
        tool_count = 1

    return {
        "agent": True,
        "tool_call": tool_call,
        "tool_result": tool_result,
        "trace": trace or [],
        "tool_count": tool_count,
        "version": "agent-v1",
    }


def run_agent_persisted(query, kb_name=None, tools=None, conversation_id=None, user_id=None):
    """负责 run_agent_persisted 的函数职责。"""
    if conversation_id is None:
        conversation_id = create_conversation(query, user_id=user_id)
    elif get_conversation(conversation_id, user_id=user_id) is None:
        return {
            "answer": "",
            "tool_call": None,
            "tool_result": None,
            "trace": [],
            "error": "conversation not found",
        }

    save_message(conversation_id, "user", query, user_id=user_id)
    result = run_agent(
        query,
        kb_name=kb_name,
        tools=tools,
        user_id=user_id,
    )
    metadata = build_agent_metadata(
        result.get("tool_call"),
        result.get("tool_result"),
        result.get("trace"),
    )
    assistant_message_id = save_message(
        conversation_id,
        "assistant",
        result.get("answer") or result.get("error") or "",
        metadata=metadata,
        user_id=user_id,
    )

    return {
        **result,
        "conversation_id": conversation_id,
        "assistant_message_id": assistant_message_id,
        "chat_history": get_conversation_messages(conversation_id, user_id=user_id),
    }


def run_agent_multi_step_persisted(
    query,
    kb_name=None,
    tools=None,
    max_steps=3,
    conversation_id=None,
    user_id=None,
):
    """负责 run_agent_multi_step_persisted 的函数职责。"""
    if conversation_id is None:
        conversation_id = create_conversation(query, user_id=user_id)
    elif get_conversation(conversation_id, user_id=user_id) is None:
        return {
            "answer": "",
            "steps": [],
            "trace": [],
            "tool_count": 0,
            "error": "conversation not found",
        }

    save_message(conversation_id, "user", query, user_id=user_id)
    result = run_agent_multi_step(
        query,
        kb_name=kb_name,
        tools=tools,
        max_steps=max_steps,
        user_id=user_id,
    )
    metadata = build_multi_step_metadata(result)
    assistant_message_id = save_message(
        conversation_id,
        "assistant",
        result.get("answer") or result.get("error") or "",
        metadata=metadata,
        user_id=user_id,
    )

    return {
        **result,
        "conversation_id": conversation_id,
        "assistant_message_id": assistant_message_id,
        "chat_history": get_conversation_messages(conversation_id, user_id=user_id),
    }


def run_agent_planner_persisted(
    query,
    kb_name=None,
    tools=None,
    max_steps=3,
    conversation_id=None,
    user_id=None,
):
    """负责 run_agent_planner_persisted 的函数职责。"""
    if conversation_id is None:
        conversation_id = create_conversation(query, user_id=user_id)
    elif get_conversation(conversation_id, user_id=user_id) is None:
        return {
            "answer": "",
            "steps": [],
            "trace": [],
            "tool_count": 0,
            "error": "conversation not found",
        }

    save_message(conversation_id, "user", query, user_id=user_id)
    result = run_agent_with_planner(
        query,
        kb_name=kb_name,
        tools=tools,
        max_steps=max_steps,
        user_id=user_id,
    )
    metadata = build_planner_metadata(result)
    assistant_message_id = save_message(
        conversation_id,
        "assistant",
        result.get("answer") or result.get("error") or "",
        metadata=metadata,
        user_id=user_id,
    )

    return {
        **result,
        "conversation_id": conversation_id,
        "assistant_message_id": assistant_message_id,
        "chat_history": get_conversation_messages(conversation_id, user_id=user_id),
    }


def run_agent_planner_stream_persisted(
    query,
    kb_name=None,
    tools=None,
    max_steps=3,
    conversation_id=None,
    event_sink=None,
    should_stop=None,
    user_id=None,
):
    """负责 run_agent_planner_stream_persisted 的函数职责。"""
    if conversation_id is None:
        conversation_id = create_conversation(query, user_id=user_id)
    elif get_conversation(conversation_id, user_id=user_id) is None:
        return {
            "answer": "",
            "steps": [],
            "trace": [],
            "tool_count": 0,
            "error": "conversation not found",
        }

    save_message(conversation_id, "user", query, user_id=user_id)
    result = run_agent_with_planner(
        query,
        kb_name=kb_name,
        tools=tools,
        max_steps=max_steps,
        event_sink=event_sink,
        should_stop=should_stop,
        user_id=user_id,
    )
    metadata = build_planner_metadata(result)
    assistant_message_id = save_message(
        conversation_id,
        "assistant",
        result.get("answer") or result.get("error") or "",
        metadata=metadata,
        user_id=user_id,
    )

    return {
        **result,
        "conversation_id": conversation_id,
        "assistant_message_id": assistant_message_id,
        "chat_history": get_conversation_messages(conversation_id, user_id=user_id),
    }
