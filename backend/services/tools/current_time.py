from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .types import ToolResult, ToolSpec


def format_utc_offset(dt: datetime) -> str:
    """负责 format_utc_offset 的函数职责。"""
    offset = dt.utcoffset()
    if offset is None:
        return "+00:00"

    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60

    return f"{sign}{hours:02d}:{minutes:02d}"


def execute_current_time(arguments: dict) -> ToolResult:
    """负责 execute_current_time 的函数职责。"""
    timezone_name = arguments.get("timezone")
    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now().astimezone()

    if timezone_name is not None:
        if not isinstance(timezone_name, str) or not timezone_name.strip():
            return ToolResult(
                ok=False,
                error="timezone must be a non-empty IANA timezone string",
            )

        timezone_name = timezone_name.strip()

        try:
            selected_timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            return ToolResult(
                ok=False,
                error=f"unknown timezone: {timezone_name}",
                metadata={
                    "timezone": timezone_name,
                },
            )

        selected_time = now_utc.astimezone(selected_timezone)

        return ToolResult(
            ok=True,
            result={
                "utc": now_utc.isoformat(),
                "local": now_local.isoformat(),
                "timezone": timezone_name,
                "iso_datetime": selected_time.isoformat(),
                "readable_datetime": selected_time.strftime(
                    "%Y-%m-%d %H:%M:%S %Z"
                ),
                "utc_offset": format_utc_offset(selected_time),
            },
            metadata={
                "timezone": timezone_name,
                "local_timezone": str(now_local.tzinfo),
            },
        )

    return ToolResult(
        ok=True,
        result={
            "utc": now_utc.isoformat(),
            "local": now_local.isoformat(),
            "timezone": str(now_local.tzinfo),
            "iso_datetime": now_local.isoformat(),
            "readable_datetime": now_local.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "utc_offset": format_utc_offset(now_local),
        },
        metadata={
            "timezone": str(now_local.tzinfo),
        },
    )


def get_current_time_tool() -> ToolSpec:
    """负责 get_current_time_tool 的函数职责。"""
    return ToolSpec(
        name="current_time",
        description="Return the current UTC time and local time.",
        args_schema={
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": (
                        "Optional IANA timezone name, such as "
                        "Pacific/Auckland, Asia/Shanghai, or UTC."
                    ),
                },
            },
            "additionalProperties": False,
        },
        executor=execute_current_time,
    )
