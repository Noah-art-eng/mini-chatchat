"""Agent、内置 Tool 与 MCP Tool 的 HTTP 路由。"""

import asyncio
import json
import queue
import threading

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from agent_service import (
    decide_tool_call,
    get_available_tool_specs,
    run_agent_multi_step_persisted,
    run_agent_once,
    run_agent_persisted,
    run_agent_planner_persisted,
    run_agent_planner_stream_persisted,
)
from api.schemas import AgentToolCallRequest, ToolRunRequest
from auth.dependencies import (
    get_current_user_optional,
    get_request_user_id,
    require_permission,
)
from auth.models import CurrentUser
from auth.permissions import Permission
from services.mcp_adapter import (
    list_mcp_servers,
    list_mcp_tools,
    run_mcp_tool,
    shutdown_mcp_server,
)
from services.tools import list_all_tools, run_tool


router = APIRouter()


@router.get("/agent/tools")
def get_agent_tools():
    """负责 get_agent_tools 的函数职责。"""
    return {"tools": list_all_tools()}


@router.post("/agent/tools/{tool_name}/run")
def run_agent_tool(
    tool_name: str,
    request: ToolRunRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 run_agent_tool 的函数职责。"""
    if tool_name in {"filesystem_readonly_read", "sqlite_readonly_query"}:
        require_permission(
            current_user,
            (
                Permission.CAN_USE_FILESYSTEM
                if tool_name == "filesystem_readonly_read"
                else Permission.CAN_USE_SQLITE
            ),
        )

    arguments = dict(request.arguments or {})
    if tool_name == "kb_search":
        arguments["_user_id"] = get_request_user_id(current_user)

    return run_tool(tool_name, arguments).to_dict()


@router.get("/agent/mcp/tools")
def get_agent_mcp_tools(
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 get_agent_mcp_tools 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_MCP)
    return {"tools": list_mcp_tools(), "enabled": True, "provider": "mcp"}


@router.get("/agent/mcp/servers")
def get_agent_mcp_servers(
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 get_agent_mcp_servers 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_MCP)
    return {"servers": list_mcp_servers()}


@router.post("/agent/mcp/servers/{server_name}/shutdown")
def stop_agent_mcp_server(
    server_name: str,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 stop_agent_mcp_server 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_MCP)
    return {"server": shutdown_mcp_server(server_name)}


@router.post("/agent/mcp/tools/{tool_name}/run")
def run_agent_mcp_tool(
    tool_name: str,
    request: ToolRunRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 run_agent_mcp_tool 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_MCP)
    return run_mcp_tool(tool_name, request.arguments).to_dict()


@router.post("/agent/decide")
def agent_decide(
    request: AgentToolCallRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 agent_decide 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_AGENT)
    available_tools, error = get_available_tool_specs(request.tools)
    if error:
        return {"tool_call": None, "raw_model_output": "", "error": error}
    return decide_tool_call(request.query, available_tools)


@router.post("/agent/run_once")
def agent_run_once(
    request: AgentToolCallRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 agent_run_once 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_AGENT)
    return run_agent_once(
        request.query,
        kb_name=request.kb_name,
        tools=request.tools,
        user_id=get_request_user_id(current_user),
    )


@router.post("/agent/run")
async def agent_run(
    request: AgentToolCallRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 agent_run 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_AGENT)
    return await asyncio.to_thread(
        run_agent_persisted,
        request.query,
        kb_name=request.kb_name,
        tools=request.tools,
        conversation_id=request.conversation_id,
        user_id=get_request_user_id(current_user),
    )


@router.post("/agent/run_multi")
def agent_run_multi(
    request: AgentToolCallRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 agent_run_multi 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_AGENT)
    return run_agent_multi_step_persisted(
        request.query,
        kb_name=request.kb_name,
        tools=request.tools,
        max_steps=request.max_steps,
        conversation_id=request.conversation_id,
        user_id=get_request_user_id(current_user),
    )


@router.post("/agent/plan_run")
def agent_plan_run(
    request: AgentToolCallRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 agent_plan_run 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_AGENT)
    return run_agent_planner_persisted(
        request.query,
        kb_name=request.kb_name,
        tools=request.tools,
        max_steps=request.max_steps,
        conversation_id=request.conversation_id,
        user_id=get_request_user_id(current_user),
    )


def encode_sse(event):
    """将 Agent 事件编码成前端现有的 SSE 帧格式。"""
    event_type = event.get("type", "message")
    payload = json.dumps(event, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


@router.post("/agent/plan_run_stream")
async def agent_plan_run_stream(
    request: AgentToolCallRequest,
    http_request: Request,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 agent_plan_run_stream 的函数职责。"""
    require_permission(current_user, Permission.CAN_USE_AGENT)
    events: queue.Queue = queue.Queue()
    stop_event = threading.Event()
    user_id = get_request_user_id(current_user)

    def put_event(event):
        """将同步 Agent 线程产生的事件交给异步 SSE 响应。"""
        events.put(event)

    def run_agent_worker():
        """在后台线程运行同步 Planner Agent。"""
        try:
            result = run_agent_planner_stream_persisted(
                request.query,
                kb_name=request.kb_name,
                tools=request.tools,
                max_steps=request.max_steps,
                conversation_id=request.conversation_id,
                event_sink=put_event,
                should_stop=stop_event.is_set,
                user_id=user_id,
            )
            events.put({"type": "done", "result": result})
        except Exception as exc:
            events.put({"type": "error", "error": str(exc)})
        finally:
            events.put(None)

    async def event_stream():
        """转发线程事件，并在客户端断开时通知 Agent 停止后续阶段。"""
        worker = threading.Thread(target=run_agent_worker, daemon=True)
        worker.start()

        while True:
            if await http_request.is_disconnected():
                stop_event.set()
                break
            try:
                event = events.get(timeout=0.1)
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue
            if event is None:
                break
            yield encode_sse(event)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
