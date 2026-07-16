from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolResult:
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


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_schema: dict
    executor: Callable[[dict], ToolResult]
    provider: str = "local"
    read_only: bool = True
    risk_level: str = "low"
    server_name: str | None = None
    tool_name: str | None = None

    def public_dict(self) -> dict:
        data = {
            "name": self.name,
            "description": self.description,
            "args_schema": self.args_schema,
            "provider": self.provider,
            "read_only": self.read_only,
            "risk_level": self.risk_level,
        }

        if self.provider == "mcp":
            data.update({
                "server_name": self.server_name,
                "tool_name": self.tool_name,
                "qualified_name": self.name,
                "input_schema": self.args_schema,
            })

        return data
