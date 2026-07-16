from services.kb_service import MiniKBService

from .types import ToolResult, ToolSpec


def is_safe_kb_name(kb_name: str) -> bool:
    return (
        bool(kb_name)
        and ".." not in kb_name
        and "/" not in kb_name
        and "\\" not in kb_name
    )


def normalize_top_k(value) -> int:
    try:
        top_k = int(value)
    except (TypeError, ValueError):
        return 3

    return min(max(top_k, 1), 20)


def execute_kb_search(arguments: dict) -> ToolResult:
    query = arguments.get("query")
    kb_name = arguments.get("kb_name", "default")
    top_k = normalize_top_k(arguments.get("top_k", 3))
    metadata_filter = arguments.get("metadata_filter")

    if not isinstance(query, str) or not query.strip():
        return ToolResult(
            ok=False,
            error="query is required",
        )

    if not isinstance(kb_name, str) or not is_safe_kb_name(kb_name):
        return ToolResult(
            ok=False,
            error="invalid kb_name",
        )

    if metadata_filter is not None and not isinstance(metadata_filter, dict):
        return ToolResult(
            ok=False,
            error="metadata_filter must be an object",
        )

    try:
        kb_service = MiniKBService(kb_name)
        sources = kb_service.search_docs(
            query,
            top_k=top_k,
            metadata_filter=metadata_filter,
        )
        return ToolResult(
            ok=True,
            result={
                "query": query,
                "kb_name": kb_name,
                "sources": sources,
            },
            metadata={
                "top_k": top_k,
                "source_count": len(sources),
            },
        )
    except Exception as exc:
        return ToolResult(
            ok=False,
            error=str(exc),
        )


def get_kb_search_tool() -> ToolSpec:
    return ToolSpec(
        name="kb_search",
        description="Search a local knowledge base and return matching chunks.",
        args_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query.",
                },
                "kb_name": {
                    "type": "string",
                    "default": "default",
                    "description": "Knowledge base name.",
                },
                "top_k": {
                    "type": "integer",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 20,
                },
                "metadata_filter": {
                    "type": "object",
                    "description": "Optional source/file filter.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        executor=execute_kb_search,
    )
