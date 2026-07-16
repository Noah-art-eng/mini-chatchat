from datetime import datetime, timezone

from .types import ToolResult, ToolSpec


def execute_current_time(arguments: dict) -> ToolResult:
    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now().astimezone()

    return ToolResult(
        ok=True,
        result={
            "utc": now_utc.isoformat(),
            "local": now_local.isoformat(),
        },
        metadata={
            "timezone": str(now_local.tzinfo),
        },
    )


def get_current_time_tool() -> ToolSpec:
    return ToolSpec(
        name="current_time",
        description="Return the current UTC time and local time.",
        args_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        executor=execute_current_time,
    )
