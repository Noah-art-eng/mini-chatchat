from .mcp_client import MCPClient
from .mcp_types import MCPToolResult, MCPToolSpec


_CLIENT = MCPClient()


def get_mcp_client() -> MCPClient:
    return _CLIENT


def mcp_result_to_tool_result(result: MCPToolResult):
    from .tools.types import ToolResult

    return ToolResult(
        ok=result.ok,
        result=result.result,
        error=result.error,
        metadata=result.metadata,
    )


def mcp_spec_to_tool_spec(spec: MCPToolSpec):
    from .tools.types import ToolSpec

    def executor(arguments: dict):
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
    return get_mcp_client().list_servers()


def shutdown_mcp_server(server_name: str) -> dict:
    return get_mcp_client().shutdown_server(server_name)


def list_mcp_tool_specs() -> list[MCPToolSpec]:
    return get_mcp_client().discover_tools()


def get_mcp_tool_registry() -> dict[str, ToolSpec]:
    return {
        spec.qualified_name: mcp_spec_to_tool_spec(spec)
        for spec in list_mcp_tool_specs()
    }


def list_mcp_tools() -> list[dict]:
    return [
        tool.public_dict()
        for tool in get_mcp_tool_registry().values()
    ]


def get_mcp_tool(tool_name: str) -> ToolSpec | None:
    registry = get_mcp_tool_registry()
    if tool_name in registry:
        return registry[tool_name]

    if not tool_name.startswith("mcp."):
        return registry.get(f"mcp.{tool_name}")

    return None


def run_mcp_tool(tool_name: str, arguments: dict | None = None) -> ToolResult:
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
