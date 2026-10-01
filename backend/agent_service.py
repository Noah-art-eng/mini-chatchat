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


def decide_agent_action(query, available_tools, steps):
    # Agent 每轮只允许一个工具调用；模型不可用或输出非法时回退到确定性路由。
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
    spec = resolve_tool(tool_name)
    if spec is None or getattr(spec, "provider", "local") != "mcp":
        return {}

    return {
        "provider": "mcp",
        "server": getattr(spec, "server_name", None),
        "tool": getattr(spec, "tool_name", None),
    }


def run_agent_once(query, kb_name=None, tools=None, user_id=None):
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
    if tool_result is None:
        return ""

    return json.dumps(
        tool_result,
        ensure_ascii=False,
        indent=2,
    )


def generate_final_answer(query, tool_call, tool_result):
    tool_name = (tool_call or {}).get("tool", "none")

    if tool_result is not None and not tool_result.get("ok"):
        return (
            "I could not complete the request because the selected tool failed: "
            f"{tool_result.get('error') or 'unknown tool error'}"
        )

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
    try:
        parsed = int(max_steps)
    except (TypeError, ValueError):
        parsed = 3

    return max(1, min(parsed, MAX_AGENT_STEPS))


def tool_signature(tool_name, arguments):
    return json.dumps(
        {
            "tool": tool_name,
            "arguments": arguments or {},
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def summarize_observation(tool_result):
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
    if event_sink is not None:
        # SSE trace 仅暴露截断且脱敏后的值，避免工具输出泄漏运行时敏感信息。
        event_sink(sanitize_stream_value(event))


def stream_answer_tokens(answer):
    if not answer:
        return []

    parts = re.findall(r"\S+\s*", answer)
    return parts or [answer]


def generate_multi_step_final_answer(query, steps, fallback_answer=""):
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
    return {
        "agent": True,
        "mode": "multi-step",
        "steps": result.get("steps", []),
        "trace": result.get("trace", []),
        "tool_count": result.get("tool_count", 0),
        "version": "agent-v2",
    }


def build_planner_metadata(result):
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
