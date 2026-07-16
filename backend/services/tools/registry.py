from .browser_read import get_browser_read_tool
from .browser_search import get_browser_search_tool
from .calculator import get_calculator_tool
from .current_time import get_current_time_tool
from .filesystem_readonly import get_filesystem_readonly_read_tool
from .kb_search import get_kb_search_tool
from .sqlite_readonly import get_sqlite_readonly_query_tool
from .types import ToolResult, ToolSpec


def get_local_tool_registry() -> dict[str, ToolSpec]:
    tools = [
        get_current_time_tool(),
        get_calculator_tool(),
        get_kb_search_tool(),
        get_sqlite_readonly_query_tool(),
        get_filesystem_readonly_read_tool(),
        get_browser_read_tool(),
        get_browser_search_tool(),
    ]
    return {
        tool.name: tool
        for tool in tools
    }


def get_tool_registry() -> dict[str, ToolSpec]:
    return get_local_tool_registry()


def list_all_tools() -> list[dict]:
    from services.mcp_registry import get_mcp_tool_registry

    registry = {
        **get_local_tool_registry(),
        **get_mcp_tool_registry(),
    }
    return [
        tool.public_dict()
        for tool in registry.values()
    ]


def resolve_tool(name: str) -> ToolSpec | None:
    if name in get_local_tool_registry():
        return get_local_tool_registry()[name]

    from services.mcp_registry import get_mcp_tool_registry

    return get_mcp_tool_registry().get(name)


def get_tool(name: str) -> ToolSpec | None:
    return get_local_tool_registry().get(name)


def list_tools() -> list[dict]:
    return [
        tool.public_dict()
        for tool in get_tool_registry().values()
    ]


def run_tool(name: str, arguments: dict | None = None) -> ToolResult:
    tool = resolve_tool(name)

    if tool is None:
        return ToolResult(
            ok=False,
            error=f"tool not allowed or not found: {name}",
        )

    try:
        return tool.executor(arguments or {})
    except Exception as exc:
        return ToolResult(
            ok=False,
            error=str(exc),
        )
