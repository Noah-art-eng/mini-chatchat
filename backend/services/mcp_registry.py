from __future__ import annotations

from .mcp_client import MCPClient
from .mcp_types import MCPToolResult, MCPToolSpec


_CLIENT = MCPClient()


def get_mcp_client() -> MCPClient:
    """返回进程共享 MCPClient，避免每个请求重复启动外部 MCP 服务。"""
    return _CLIENT


def mcp_result_to_tool_result(result: MCPToolResult):
    """把 MCP 返回值转换成 Agent 本地工具统一使用的 ToolResult。"""
    from .tools.types import ToolResult

    return ToolResult(
        ok=result.ok,
        result=result.result,
        error=result.error,
        metadata=result.metadata,
    )


def mcp_spec_to_tool_spec(spec: MCPToolSpec):
    """把允许暴露的 MCP 工具描述适配成本地 ToolSpec。"""
    from .tools.types import ToolSpec

    def executor(arguments: dict):
        """把 Agent 的参数交给共享 MCPClient，并转换成统一 ToolResult。"""
        return mcp_result_to_tool_result(
            get_mcp_client().call_tool(spec.qualified_name, arguments)
        )

    return ToolSpec(
        name=spec.qualified_name,
        description=spec.description,
        args_schema=spec.input_schema,
        executor=executor,
        provider=spec.provider,
        read_only=spec.read_only,
        risk_level=spec.risk_level,
        server_name=spec.server_name,
        tool_name=spec.tool_name,
    )


def list_mcp_servers() -> list[dict]:
    """返回所有 MCP 服务的可用状态；外部服务失败不会影响本地工具。"""
    return get_mcp_client().list_servers()


def shutdown_mcp_server(server_name: str) -> dict:
    """停止指定 stdio MCP 服务并释放对应进程。"""
    return get_mcp_client().shutdown_server(server_name)


def list_mcp_tool_specs() -> list[MCPToolSpec]:
    """发现可用 MCP 工具，并返回 Agent 能理解的工具描述。"""
    return get_mcp_client().discover_tools()


def get_mcp_tool_registry() -> dict[str, ToolSpec]:
    """把已发现且允许暴露的 MCP 工具整理成 Agent 工具注册表。"""
    return {
        spec.qualified_name: mcp_spec_to_tool_spec(spec)
        for spec in list_mcp_tool_specs()
    }


def list_mcp_tools() -> list[dict]:
    """返回 MCP 工具的公开描述，供 API 和 Agent prompt 使用。"""
    return [
        tool.public_dict()
        for tool in get_mcp_tool_registry().values()
    ]


def get_mcp_tool(tool_name: str) -> ToolSpec | None:
    """按完整名称查找 MCP 工具，兼容省略 mcp. 前缀的调用。"""
    registry = get_mcp_tool_registry()
    if tool_name in registry:
        return registry[tool_name]

    if not tool_name.startswith("mcp."):
        return registry.get(f"mcp.{tool_name}")

    return None


def run_mcp_tool(tool_name: str, arguments: dict | None = None) -> ToolResult:
    """通过共享 MCPClient 执行工具，并保持本地工具相同的结果协议。"""
    tool = get_mcp_tool(tool_name)
    if tool is None:
        from .tools.types import ToolResult

        return ToolResult(
            ok=False,
            error=f"MCP tool not allowed or not found: {tool_name}",
            metadata={
                "provider": "mcp",
            },
        )

    return tool.executor(arguments or {})
