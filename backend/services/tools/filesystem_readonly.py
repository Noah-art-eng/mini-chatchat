import os
import re

from .types import ToolResult, ToolSpec


PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
    )
)
MAX_READ_CHARS = 12000
SENSITIVE_MARKERS = (
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
)
ALLOWED_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


def validate_relative_path(path: str) -> str | None:
    """负责 validate_relative_path 的函数职责。"""
    if not path.strip():
        return "path is required"

    if os.path.isabs(path):
        return "absolute paths are not allowed"

    normalized_parts = path.replace("\\", "/").split("/")
    if ".." in normalized_parts:
        return "parent directory traversal is not allowed"

    extension = os.path.splitext(path)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return f"file extension is not allowed: {extension or '(none)'}"

    target_path = os.path.abspath(os.path.join(PROJECT_ROOT, path))
    if not target_path.startswith(PROJECT_ROOT + os.sep):
        return "path must stay inside project root"

    if not os.path.isfile(target_path):
        return "file not found"

    return None


def execute_filesystem_readonly_read(arguments: dict) -> ToolResult:
    """负责 execute_filesystem_readonly_read 的函数职责。"""
    path = arguments.get("path")

    if not isinstance(path, str):
        return ToolResult(
            ok=False,
            error="path must be a string",
        )

    validation_error = validate_relative_path(path)
    if validation_error:
        return ToolResult(
            ok=False,
            error=validation_error,
        )

    target_path = os.path.abspath(os.path.join(PROJECT_ROOT, path))

    try:
        with open(target_path, "r", encoding="utf-8", errors="replace") as file:
            content = file.read(MAX_READ_CHARS + 1)
    except OSError as exc:
        return ToolResult(
            ok=False,
            error=str(exc),
        )

    truncated = len(content) > MAX_READ_CHARS
    if truncated:
        content = content[:MAX_READ_CHARS]

    for marker in SENSITIVE_MARKERS:
        content = re.sub(
            marker,
            "[REDACTED_ENV_NAME]",
            content,
            flags=re.IGNORECASE,
        )

    return ToolResult(
        ok=True,
        result={
            "path": path,
            "content": content,
            "char_count": len(content),
            "truncated": truncated,
        },
        metadata={
            "readonly": True,
            "project_root": PROJECT_ROOT,
        },
    )


def get_filesystem_readonly_read_tool() -> ToolSpec:
    """负责 get_filesystem_readonly_read_tool 的函数职责。"""
    return ToolSpec(
        name="filesystem_readonly_read",
        description=(
            "Read a text file from the Mini ChatChat project using a safe "
            "relative path. Use for inspecting project source files or docs. "
            "This tool is read-only and cannot access files outside the "
            "project root."
        ),
        args_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Relative path from the project root, for example "
                        "README.md or backend/app.py."
                    ),
                }
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        executor=execute_filesystem_readonly_read,
    )
