from services.kb_service import MiniKBService
from db import user_owns_kb

from .types import ToolResult, ToolSpec
from path_security import is_safe_kb_name


def normalize_top_k(value) -> int:
    """把模型传入的 top_k 限制在工具允许的 1～20 条范围内。"""
    try:
        top_k = int(value)
    except (TypeError, ValueError):
        return 3

    return min(max(top_k, 1), 20)


def execute_kb_search(arguments: dict) -> ToolResult:
    """在当前用户拥有的知识库中执行混合检索。

    Agent 传入的 `_user_id` 由运行时注入，不信任模型自行指定。这里先验证知识库
    归属，再进入 MiniKBService.search_docs()，最后把文本块包装成统一工具结果。
    """
    query = arguments.get("query")
    kb_name = arguments.get("kb_name", "default")
    top_k = normalize_top_k(arguments.get("top_k", 3))
    metadata_filter = arguments.get("metadata_filter")
    user_id = arguments.get("_user_id")

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

    # 工具不能借 kb_name 查询其他用户的知识库。
    if not user_owns_kb(kb_name, user_id=user_id):
        return ToolResult(
            ok=False,
            error="knowledge base not found",
        )

    try:
        kb_service = MiniKBService(kb_name, user_id=user_id)
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
    """声明知识库检索工具的参数边界，并把执行入口交给工具注册表。"""
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
