from services.search_service import search_web

from .types import ToolResult, ToolSpec


MAX_RESULTS = 5


def normalize_max_results(value) -> int:
    """限制联网搜索返回数量，避免模型请求过大的外部结果集。"""
    try:
        max_results = int(value)
    except (TypeError, ValueError):
        return 3

    return min(max(max_results, 1), MAX_RESULTS)


def execute_browser_search(arguments: dict) -> ToolResult:
    """调用受控搜索适配器，并把不同字段整理成统一的标题、链接和摘要。"""
    query = arguments.get("query")
    max_results = normalize_max_results(arguments.get("max_results", 3))

    if not isinstance(query, str) or not query.strip():
        return ToolResult(
            ok=False,
            error="query is required",
        )

    try:
        docs = search_web(query.strip(), top_k=max_results)
    except Exception as exc:
        return ToolResult(
            ok=False,
            error=str(exc),
        )

    results = [
        {
            "title": doc.get("title") or "",
            "url": doc.get("source") or doc.get("url") or "",
            "snippet": doc.get("chunk") or doc.get("content") or "",
        }
        for doc in docs[:max_results]
    ]

    return ToolResult(
        ok=True,
        result={
            "query": query.strip(),
            "results": results,
            "result_count": len(results),
        },
        metadata={
            "max_results": max_results,
            "controlled": True,
        },
    )


def get_browser_search_tool() -> ToolSpec:
    """声明只做搜索、不读取网页或执行浏览器操作的联网搜索工具。"""
    return ToolSpec(
        name="browser_search",
        description=(
            "Search the web through a controlled search adapter and return "
            "title, url, and snippet results. Use for current public web "
            "information. This tool does not click pages, run browser "
            "automation, execute shell commands, or write files."
        ),
        args_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Web search query.",
                },
                "max_results": {
                    "type": "integer",
                    "default": 3,
                    "minimum": 1,
                    "maximum": MAX_RESULTS,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        executor=execute_browser_search,
    )
