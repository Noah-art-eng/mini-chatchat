from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MCPToolSpec:
    """MCP 服务发现结果转换后的统一工具描述。"""
    server_name: str
    tool_name: str
    qualified_name: str
    description: str
    input_schema: dict
    provider: str = "mcp"
    read_only: bool = True
    risk_level: str = "low"

    def public_dict(self) -> dict:
        return {
            "server_name": self.server_name,
            "tool_name": self.tool_name,
            "qualified_name": self.qualified_name,
            "name": self.qualified_name,
            "description": self.description,
            "input_schema": self.input_schema,
            "args_schema": self.input_schema,
            "provider": self.provider,
            "read_only": self.read_only,
            "risk_level": self.risk_level,
        }


@dataclass(frozen=True)
class MCPToolResult:
    """MCP 调用在超时、清理和错误归一化后的统一结果。"""
    ok: bool
    result: Any = None
    error: str | None = None
    metadata: dict | None = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata or {},
        }
