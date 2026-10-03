import json
import re

from agent_fallback import (
    KB_SEARCH_TERMS,
    TIME_QUERY_TERMS,
    TIMEZONE_MAPPINGS,
    URL_PATTERN,
    WEB_SEARCH_TERMS,
    choose_multi_step_action_without_llm,
    choose_tool_without_llm,
    generate_plan_without_llm,
    infer_timezone_from_query,
    is_kb_query,
    is_time_query,
    is_web_search_query,
    query_contains_any,
)
from agent_protocol import (
    ALLOWED_AGENT_ACTION_KEYS,
    ALLOWED_PLAN_KEYS,
    ALLOWED_PLAN_STEP_KEYS,
    ALLOWED_TOOL_KEYS,
    PLAN_STATUSES,
    build_final_answer_prompt,
    build_multi_step_final_answer_prompt,
    build_multi_step_prompt,
    build_plan_prompt,
    build_tool_call_prompt,
    extract_json_object,
    normalize_plan_step,
    normalize_tool_spec,
    parse_agent_action,
    parse_plan,
    parse_tool_call,
)
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


MAX_AGENT_STEPS = 5
OBSERVATION_MAX_CHARS = 1800
STREAM_VALUE_MAX_CHARS = 1200
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


def get_available_tool_specs(tool_names=None):
    """准备本次 Agent 可以使用的工具清单，并拒绝不存在的显式工具名。"""
    # 显式指定本地工具时无需探测 MCP，避免无关的 MCP 冷启动拖慢 Agent。
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


def generate_plan(query):
    """让 Planner 把用户目标拆成步骤；模型失败时返回确定性计划。"""
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
    """为单步 Agent 选择一次工具调用，并校验模型返回的结构。

    LLM 决策和确定性规则同时准备。模型不可用时直接使用回退结果；模型输出可解析
    时仍保留少量纠偏，避免明显的时间、知识库或数据库请求被错误跳过。
    """
    prompt = build_tool_call_prompt(query, available_tools)
    fallback = choose_tool_without_llm(query, available_tools)

    # 先让 LLM 根据工具描述做选择；网络或配置失败时不让整个 Agent 中断。
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

    # 从这里进入 agent_protocol.parse_tool_call()，只接受约定的 JSON 结构和工具名。
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


def decide_agent_action(query, available_tools, steps):
    """根据已有 observation 决定多步 Agent 的下一次工具调用或最终回答。"""
    # Agent 每轮只允许一个工具调用；模型不可用或输出非法时回退到确定性路由。
    prompt = build_multi_step_prompt(query, available_tools, steps)
    fallback = choose_multi_step_action_without_llm(query, available_tools, steps)

    # 每一轮都把已有步骤交给模型，让它决定继续调用工具还是结束。
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

    # 结构不合法时使用确定性动作，保证 Agent 仍能有界地继续或结束。
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

    # 模型重复选择已经执行过的工具，而回退规则认为可以结束时，优先停止重复调用。
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
    """补齐工具所需的上下文参数，并把用户范围安全注入知识库工具。"""
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
    """用户明确点名 MCP 工具时补入工具列表；普通请求不会自动扩大 MCP 权限。"""
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
    """提取工具来源和风险信息，供 trace 与前端开发者面板展示。"""
    spec = resolve_tool(tool_name)
    if spec is None or getattr(spec, "provider", "local") != "mcp":
        return {}

    return {
        "provider": "mcp",
        "server": getattr(spec, "server_name", None),
        "tool": getattr(spec, "tool_name", None),
    }


def run_agent_once(query, kb_name=None, tools=None, user_id=None):
    """执行单步 Agent 的“准备工具 → 选择 → 调用 → 记录 trace”流程。

    这个函数不生成最终自然语言回答。它返回工具调用、结果和 trace，随后
    run_agent() 会进入 generate_final_answer() 组织面向用户的答案。
    """
    # 用户显式点名 MCP 能力时才扩展列表，再取得本轮允许暴露给模型的工具规格。
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

    # 从这里进入 decide_tool_call()；返回后先把决策原文写入 trace 便于诊断。
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

    # 模型只提供业务参数。用户范围和可推导默认值由运行时补入，不能交给模型伪造。
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

    # 进入工具注册表执行 local 或 MCP 工具；统一结果随后成为 trace observation。
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
    """把单步工具结果整理成最终回答 Prompt 可读的 observation。"""
    if tool_result is None:
        return ""

    return json.dumps(
        tool_result,
        ensure_ascii=False,
        indent=2,
    )


def generate_final_answer(query, tool_call, tool_result):
    """把单步工具 observation 交给 LLM，生成面向用户的最终回答。

    工具失败直接返回稳定说明，不再要求 LLM解释错误。工具成功时把结构化结果放进
    final-answer Prompt；模型失败则保留 observation 并返回可诊断的回退文本。
    """
    tool_name = (tool_call or {}).get("tool", "none")

    if tool_result is not None and not tool_result.get("ok"):
        return (
            "I could not complete the request because the selected tool failed: "
            f"{tool_result.get('error') or 'unknown tool error'}"
        )

    # 结构化工具结果先转成 Prompt 可读文本，再进入 agent_protocol 的回答模板。
    observation = summarize_tool_result(tool_result)
    prompt = build_final_answer_prompt(query, tool_name, observation)

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
    """把外部 max_steps 限制在 Agent 允许范围，防止异常长循环。"""
    try:
        parsed = int(max_steps)
    except (TypeError, ValueError):
        parsed = 3

    return max(1, min(parsed, MAX_AGENT_STEPS))


def tool_signature(tool_name, arguments):
    """用工具名和规范化参数生成重复调用标识。"""
    return json.dumps(
        {
            "tool": tool_name,
            "arguments": arguments or {},
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def summarize_observation(tool_result):
    """压缩工具结果供下一步决策使用，避免 observation 无限制增长。"""
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
    """把 Agent 事件转换成可安全 JSON 序列化的数据。"""
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
    """存在事件接收器时发送 Agent 进度；非流式调用可以不提供。"""
    if event_sink is not None:
        # SSE trace 仅暴露截断且脱敏后的值，避免工具输出泄漏运行时敏感信息。
        event_sink(sanitize_stream_value(event))


def stream_answer_tokens(answer):
    """把已生成的最终回答切成较小片段，供 Agent SSE 渐进回放。"""
    if not answer:
        return []

    parts = re.findall(r"\S+\s*", answer)
    return parts or [answer]


def generate_multi_step_final_answer(query, steps, fallback_answer=""):
    """根据步骤 observation 生成最终回答；已有 final_answer 时直接使用。"""
    if fallback_answer:
        return fallback_answer

    prompt = build_multi_step_final_answer_prompt(query, steps)

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
    """整理多步 Agent 的步骤、trace 和工具次数，随助手消息持久化。"""
    return {
        "agent": True,
        "mode": "multi-step",
        "steps": result.get("steps", []),
        "trace": result.get("trace", []),
        "tool_count": result.get("tool_count", 0),
        "version": "agent-v2",
    }


def build_planner_metadata(result):
    """在多步 metadata 上增加 planner 状态，供历史会话恢复执行详情。"""
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
    """把实际执行结果逐步回填到计划，供前端展示真实进度。

    工具成功或失败分别落到对应计划步骤；一旦失败，尚未执行的步骤标为 skipped。
    如果 Agent 提前生成最终回答，则只推进下一个待执行步骤，避免一次结果越过多步。
    """
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

    # 按执行顺序把 observation 对齐到计划，不让多余执行结果越出原计划范围。
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

    # 失败后剩余计划不再执行；正常提前回答则只完成一个当前步骤。
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
    """运行受步数、重复调用和客户端断连保护的多步 Agent 循环。

    每轮先决定 action，再校验工具和参数签名，最后执行工具并记录 observation。
    循环结束后才生成最终回答；客户端已断开时跳过新的工具和 LLM 调用。
    """
    max_steps = normalize_max_steps(max_steps)
    # 先展开请求明确需要的 MCP 工具，再取得统一工具描述。工具不存在时在进入循环前
    # 返回，避免模型规划一个实际无法执行的动作。
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
        # 每轮开始和耗时决策返回后都检查断连。已经发出的 SDK 请求不强制取消，
        # 但断连后不会再启动新的工具或最终总结。
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

        # 工具名先经过允许列表验证，再执行重复签名保护。这样既阻止模型调用未授权
        # 工具，也避免相同参数在多步循环里反复执行。
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

        # 工具结果先压缩成下一轮决策可读的 observation，同时保留完整结构供 trace
        # 和持久化使用。随后循环回到下一步，或在达到上限后结束。
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
    """先生成计划，再运行多步 Agent，并把执行结果回填为 Planner 状态。

    事件会按 planning、tool、planner update、token 的顺序交给 SSE 层。这里的 token
    是最终文本生成完成后的分段回放，不是 LLM 原生 token streaming。
    """
    planner = generate_plan(query)
    # planner 只生成计划，不执行工具。计划先通过 planning 事件交给前端，然后由
    # run_agent_multi_step() 按同一套停止、重复调用和最大步数保护真正执行。
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
    # 多步结果返回后只推进一次计划状态，再发送 planner_update 供前端刷新步骤。
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
    # 最终回答此时已经生成。这里把文本切片成 token 事件供界面渐进展示，
    # 不是直接转发模型原生流；回放期间仍检查客户端是否已经停止。
    for token in stream_answer_tokens(result.get("answer", "")):
        if should_stop is not None and should_stop():
            break
        emit_agent_event(event_sink, {
            "type": "token",
            "content": token,
        })

    return result


def run_agent(query, kb_name=None, tools=None, user_id=None):
    """执行单步 Agent，并在工具完成后生成最终回答。"""
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
    """整理单步 Agent 的工具调用和 trace，随助手消息保存。"""
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
    """把单步 Agent 包装成会话流程，持久化用户消息、回答和 trace metadata。"""
    # 会话创建和读取都带 user_id，避免把 Agent 消息写入其他用户的会话。
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

    # 先保存用户问题，再运行 Agent；最终 trace 会随助手消息一起保存。
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
    """运行多步 Agent，并把步骤、工具结果和最终回答保存到当前用户会话。"""
    # 持久化包装层不改变多步控制流，只管理用户会话和最终 metadata。
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
    """运行 Planner Agent，并把计划状态、trace 和回答持久化到会话。"""
    # planner 的计划、步骤和观察结果整体写入助手消息，刷新后仍能恢复执行详情。
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
    """为 SSE 路由运行可停止的 Planner Agent，并在结束后保存完整执行记录。"""
    # SSE 事件用于当前页面实时展示；结束后仍保存同一份最终结果作为历史事实来源。
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
