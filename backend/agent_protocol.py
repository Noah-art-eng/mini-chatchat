import json
import re


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


def normalize_tool_spec(tool):
    """将工具对象转换为 Agent prompt 使用的公开描述。"""
    if hasattr(tool, "public_dict"):
        return tool.public_dict()

    return tool


def build_tool_call_prompt(query, available_tools):
    """构造单步 Agent 选择工具时使用的原始 prompt。"""
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
    """从模型回复中提取可能被代码块或说明文字包围的 JSON 对象。"""
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
    """校验并规范化单步工具选择模型返回的 JSON。"""
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
    """校验并规范化多步 Agent 控制器返回的 JSON。"""
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
    """将模型生成的单个计划步骤整理为固定协议结构。"""
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
    """校验 planner JSON，并补齐运行阶段依赖的计划字段。"""
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


def build_plan_prompt(query):
    """构造 planner 将用户请求拆成步骤时使用的原始 prompt。"""
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


def build_multi_step_prompt(query, available_tools, steps):
    """构造多步 Agent 决定下一步动作时使用的原始 prompt。"""
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


def build_final_answer_prompt(query, tool_name, observation):
    """构造单步工具执行完成后生成最终回答的 prompt。"""
    return f"""
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


def build_multi_step_final_answer_prompt(query, steps):
    """构造多步工具观察汇总为最终回答时使用的 prompt。"""
    observations = json.dumps(
        steps,
        ensure_ascii=False,
        indent=2,
    )
    return f"""
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
