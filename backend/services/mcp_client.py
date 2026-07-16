from __future__ import annotations

import concurrent.futures
import os
import re
from typing import Callable

from .mcp_types import MCPToolResult, MCPToolSpec
from .mcp_transport import StdioMCPServer, StdioMCPServerConfig


PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
    )
)
SQLITE_DB_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "mini.db",
    )
)
MAX_READ_CHARS = 12000
MAX_LIST_ENTRIES = 200
ALLOWED_MCP_SERVERS = {"demo", "filesystem", "filesystem_stdio", "sqlite"}
ALLOWED_MCP_TOOLS = {
    "demo": {"echo", "server_info"},
    "filesystem": {"read_file", "list_dir"},
    "filesystem_stdio": {
        "read_file",
        "read_multiple_files",
        "list_directory",
        "directory_tree",
        "search_files",
        "get_file_info",
        "list_allowed_directories",
    },
    "sqlite": {
        "query",
        "describe-table",
        "list-tables",
    },
}
MCP_TIMEOUT_SECONDS = 5
FORBIDDEN_ERROR_FRAGMENTS = (
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "invalid_api_key",
    "OpenAI 401",
    "MCP command",
    "environment",
    "stderr",
)
SENSITIVE_MARKERS = (
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
)
ALLOWED_FILE_EXTENSIONS = {
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
BLOCKED_PATH_NAMES = {
    ".env",
    "mini.db",
}


class DemoMCPServer:
    name = "demo"

    def list_tools(self) -> list[MCPToolSpec]:
        return [
            MCPToolSpec(
                server_name=self.name,
                tool_name="echo",
                qualified_name="mcp.demo.echo",
                description=(
                    "Echo a short message through the demo MCP server. Use this "
                    "only to verify MCP tool discovery and call plumbing."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Short message to echo back.",
                        }
                    },
                    "required": ["message"],
                    "additionalProperties": False,
                },
                read_only=True,
                risk_level="low",
            ),
            MCPToolSpec(
                server_name=self.name,
                tool_name="server_info",
                qualified_name="mcp.demo.server_info",
                description=(
                    "Return non-sensitive demo MCP server information. Use this "
                    "only to verify MCP server discovery."
                ),
                input_schema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                read_only=True,
                risk_level="low",
            ),
        ]

    def call_tool(self, tool_name: str, arguments: dict) -> MCPToolResult:
        if tool_name == "echo":
            message = arguments.get("message")
            if not isinstance(message, str) or not message.strip():
                return MCPToolResult(
                    ok=False,
                    error="message must be a non-empty string",
                    metadata=self._metadata(tool_name),
                )

            return MCPToolResult(
                ok=True,
                result={
                    "message": message,
                },
                metadata=self._metadata(tool_name),
            )

        if tool_name == "server_info":
            return MCPToolResult(
                ok=True,
                result={
                    "server": self.name,
                    "tool_count": len(self.list_tools()),
                    "provider": "mcp",
                    "enabled": True,
                },
                metadata=self._metadata(tool_name),
            )

        return MCPToolResult(
            ok=False,
            error=f"MCP tool not allowed or not found: {self.name}.{tool_name}",
            metadata={
                "server": self.name,
                "tool": tool_name,
                "provider": "mcp",
            },
        )

    def _metadata(self, tool_name: str) -> dict:
        return {
            "server": self.name,
            "tool": tool_name,
            "provider": "mcp",
            "read_only": True,
            "risk_level": "low",
        }


class FilesystemMCPServer:
    name = "filesystem"

    def list_tools(self) -> list[MCPToolSpec]:
        return [
            MCPToolSpec(
                server_name=self.name,
                tool_name="read_file",
                qualified_name="mcp.filesystem.read_file",
                description=(
                    "Read a text file from the Mini ChatChat project using a safe "
                    "relative path. This MCP tool is read-only and cannot access "
                    "paths outside the project root."
                ),
                input_schema={
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
                read_only=True,
                risk_level="low",
            ),
            MCPToolSpec(
                server_name=self.name,
                tool_name="list_dir",
                qualified_name="mcp.filesystem.list_dir",
                description=(
                    "List files and directories under a safe project-relative "
                    "directory. This MCP tool is read-only."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Relative directory path from the project root. "
                                "Use an empty string or . for the project root."
                            ),
                        }
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
                read_only=True,
                risk_level="low",
            ),
        ]

    def call_tool(self, tool_name: str, arguments: dict) -> MCPToolResult:
        if tool_name == "read_file":
            return self._read_file(arguments)

        if tool_name == "list_dir":
            return self._list_dir(arguments)

        return MCPToolResult(
            ok=False,
            error=f"MCP tool not allowed or not found: {self.name}.{tool_name}",
            metadata=self._metadata(tool_name),
        )

    def _read_file(self, arguments: dict) -> MCPToolResult:
        path = arguments.get("path")
        if not isinstance(path, str):
            return self._error("path must be a string", "read_file")

        validation_error = self._validate_file_path(path)
        if validation_error:
            return self._error(validation_error, "read_file")

        target_path = self._resolve_path(path)

        try:
            with open(target_path, "r", encoding="utf-8", errors="replace") as file:
                content = file.read(MAX_READ_CHARS + 1)
        except OSError:
            return self._error("file could not be read", "read_file")

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

        return MCPToolResult(
            ok=True,
            result={
                "path": self._normalize_path(path),
                "content": content,
                "char_count": len(content),
                "truncated": truncated,
            },
            metadata=self._metadata("read_file"),
        )

    def _list_dir(self, arguments: dict) -> MCPToolResult:
        path = arguments.get("path")
        if not isinstance(path, str):
            return self._error("path must be a string", "list_dir")

        validation_error = self._validate_dir_path(path)
        if validation_error:
            return self._error(validation_error, "list_dir")

        target_path = self._resolve_path(path)

        try:
            names = sorted(os.listdir(target_path))[:MAX_LIST_ENTRIES]
        except OSError:
            return self._error("directory could not be listed", "list_dir")

        entries = []
        for name in names:
            if name in BLOCKED_PATH_NAMES:
                continue

            entry_path = os.path.join(target_path, name)
            relative_path = os.path.relpath(entry_path, PROJECT_ROOT)
            entries.append({
                "name": name,
                "path": "." if relative_path == "." else relative_path,
                "type": "directory" if os.path.isdir(entry_path) else "file",
            })

        return MCPToolResult(
            ok=True,
            result={
                "path": self._normalize_path(path),
                "entries": entries,
                "truncated": len(names) >= MAX_LIST_ENTRIES,
            },
            metadata=self._metadata("list_dir"),
        )

    def _validate_file_path(self, path: str) -> str | None:
        common_error = self._validate_common_path(path)
        if common_error:
            return common_error

        normalized = self._normalize_path(path)
        if os.path.basename(normalized) in BLOCKED_PATH_NAMES:
            return "path is blocked by safety policy"

        extension = os.path.splitext(normalized)[1].lower()
        if extension not in ALLOWED_FILE_EXTENSIONS:
            return f"file extension is not allowed: {extension or '(none)'}"

        target_path = self._resolve_path(normalized)
        if not os.path.isfile(target_path):
            return "file not found"

        return None

    def _validate_dir_path(self, path: str) -> str | None:
        common_error = self._validate_common_path(path)
        if common_error:
            return common_error

        normalized = self._normalize_path(path)
        if os.path.basename(normalized) in BLOCKED_PATH_NAMES:
            return "path is blocked by safety policy"

        target_path = self._resolve_path(normalized)
        if not os.path.isdir(target_path):
            return "directory not found"

        return None

    def _validate_common_path(self, path: str) -> str | None:
        if not path.strip():
            return "path is required"

        if os.path.isabs(path):
            return "absolute paths are not allowed"

        normalized = self._normalize_path(path)
        parts = normalized.split("/")
        if ".." in parts:
            return "parent directory traversal is not allowed"

        target_path = self._resolve_path(normalized)
        if target_path != PROJECT_ROOT and not target_path.startswith(PROJECT_ROOT + os.sep):
            return "path must stay inside project root"

        return None

    def _normalize_path(self, path: str) -> str:
        normalized = path.replace("\\", "/").strip()
        if normalized in {"", "."}:
            return "."
        return normalized.strip("/")

    def _resolve_path(self, path: str) -> str:
        return os.path.abspath(os.path.join(PROJECT_ROOT, self._normalize_path(path)))

    def _error(self, message: str, tool_name: str) -> MCPToolResult:
        return MCPToolResult(
            ok=False,
            error=message,
            metadata=self._metadata(tool_name),
        )

    def _metadata(self, tool_name: str) -> dict:
        return {
            "server": self.name,
            "tool": tool_name,
            "provider": "mcp",
            "read_only": True,
            "risk_level": "low",
        }


class MCPClient:
    def __init__(self, servers: dict[str, object] | None = None):
        self.servers = servers or {
            "demo": DemoMCPServer(),
            "filesystem": FilesystemMCPServer(),
            "filesystem_stdio": StdioMCPServer(
                StdioMCPServerConfig(
                    server_name="filesystem_stdio",
                    command=os.getenv("MINI_CHATCHAT_MCP_FILESYSTEM_COMMAND", "npx"),
                    args=[
                        "-y",
                        os.getenv(
                            "MINI_CHATCHAT_MCP_FILESYSTEM_PACKAGE",
                            "mcp-server-filesystem",
                        ),
                        PROJECT_ROOT,
                    ],
                    cwd=PROJECT_ROOT,
                    env_allowlist=[
                        "HOME",
                        "PATH",
                        "npm_config_cache",
                        "npm_config_prefix",
                        "npm_config_offline",
                        "npm_config_prefer_offline",
                    ],
                    startup_timeout=float(os.getenv("MINI_CHATCHAT_MCP_STARTUP_TIMEOUT", "90")),
                    call_timeout=float(os.getenv("MINI_CHATCHAT_MCP_CALL_TIMEOUT", "15")),
                )
            ),
            "sqlite": StdioMCPServer(
                StdioMCPServerConfig(
                    server_name="sqlite",
                    command=os.getenv("MINI_CHATCHAT_MCP_SQLITE_COMMAND", "npx"),
                    args=[
                        "-y",
                        os.getenv(
                            "MINI_CHATCHAT_MCP_SQLITE_PACKAGE",
                            "mcp-server-sqlite",
                        ),
                    ],
                    cwd=PROJECT_ROOT,
                    env_allowlist=[
                        "HOME",
                        "PATH",
                        "npm_config_cache",
                        "npm_config_prefix",
                        "npm_config_offline",
                        "npm_config_prefer_offline",
                    ],
                    env={
                        "SQLITE_DB_PATH": SQLITE_DB_PATH,
                    },
                    startup_timeout=float(os.getenv("MINI_CHATCHAT_MCP_STARTUP_TIMEOUT", "90")),
                    call_timeout=float(os.getenv("MINI_CHATCHAT_MCP_CALL_TIMEOUT", "15")),
                )
            ),
        }

    def list_servers(self) -> list[dict]:
        servers = []
        for server_name in sorted(self.servers):
            server = self.servers[server_name]
            if hasattr(server, "status"):
                status = server.status()
                status["enabled"] = server_name in ALLOWED_MCP_SERVERS
                servers.append(status)
                continue

            servers.append({
                "server": server_name,
                "tool_count": self._safe_tool_count(server_name),
                "enabled": server_name in ALLOWED_MCP_SERVERS,
                "provider": "mcp",
            })
        return servers

    def discover_tools(self, server_name: str | None = None) -> list[MCPToolSpec]:
        server_names = [server_name] if server_name else sorted(self.servers)
        tools: list[MCPToolSpec] = []

        for name in server_names:
            if name not in ALLOWED_MCP_SERVERS:
                continue

            server = self.servers.get(name)
            if server is None:
                continue

            try:
                if isinstance(server, StdioMCPServer):
                    discovered = server.list_tools()
                else:
                    discovered = self._with_timeout(server.list_tools)
            except Exception:
                continue

            for tool in discovered:
                if self._is_allowed_spec(tool):
                    tools.append(tool)

        return tools

    def call_tool(self, qualified_name: str, arguments: dict | None = None) -> MCPToolResult:
        parsed = self._parse_qualified_name(qualified_name)
        if parsed is None:
            return self._error(f"MCP tool not allowed or not found: {qualified_name}")

        server_name, tool_name = parsed
        if not self._is_allowed(server_name, tool_name):
            return self._error(f"MCP tool not allowed or not found: {qualified_name}")

        spec = self.get_tool(qualified_name)
        if spec is None:
            return self._error(f"MCP tool not allowed or not found: {qualified_name}")

        if not spec.read_only or spec.risk_level != "low":
            return self._error(f"MCP tool rejected by safety policy: {qualified_name}")

        server = self.servers.get(server_name)
        if server is None:
            return self._error(f"MCP server not allowed or not found: {server_name}")

        try:
            if isinstance(server, StdioMCPServer):
                result = server.call_tool(tool_name, arguments or {})
            else:
                result = self._with_timeout(
                    lambda: server.call_tool(tool_name, arguments or {})
                )
        except TimeoutError:
            return self._error(f"MCP tool timed out: {qualified_name}")
        except Exception:
            return self._error(f"MCP tool failed: {qualified_name}")

        return self._sanitize_result(result, server_name, tool_name)

    def get_tool(self, qualified_name: str) -> MCPToolSpec | None:
        parsed = self._parse_qualified_name(qualified_name)
        if parsed is None:
            return None

        server_name, tool_name = parsed
        for tool in self.discover_tools(server_name):
            if tool.tool_name == tool_name:
                return tool

        return None

    def shutdown_server(self, server_name: str) -> dict:
        if server_name not in ALLOWED_MCP_SERVERS:
            return {
                "server": server_name,
                "enabled": False,
                "provider": "mcp",
                "running": False,
                "initialized": False,
                "tool_count": 0,
                "error": "MCP server not allowed or not found",
            }

        server = self.servers.get(server_name)
        if server is None:
            return {
                "server": server_name,
                "enabled": False,
                "provider": "mcp",
                "running": False,
                "initialized": False,
                "tool_count": 0,
                "error": "MCP server not allowed or not found",
            }

        if hasattr(server, "shutdown"):
            return server.shutdown()

        return {
            "server": server_name,
            "enabled": True,
            "provider": "mcp",
            "running": False,
            "initialized": True,
            "tool_count": self._safe_tool_count(server_name),
        }

    def _safe_tool_count(self, server_name: str) -> int:
        try:
            return len(self.discover_tools(server_name))
        except Exception:
            return 0

    def _with_timeout(self, func: Callable):
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(func)
        try:
            return future.result(timeout=MCP_TIMEOUT_SECONDS)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _parse_qualified_name(self, qualified_name: str) -> tuple[str, str] | None:
        parts = qualified_name.split(".")
        if len(parts) == 3 and parts[0] == "mcp":
            return parts[1], parts[2]

        if len(parts) == 2:
            return parts[0], parts[1]

        return None

    def _is_allowed(self, server_name: str, tool_name: str) -> bool:
        return (
            server_name in ALLOWED_MCP_SERVERS
            and tool_name in ALLOWED_MCP_TOOLS.get(server_name, set())
        )

    def _is_allowed_spec(self, tool: MCPToolSpec) -> bool:
        return (
            self._is_allowed(tool.server_name, tool.tool_name)
            and tool.provider == "mcp"
            and tool.read_only is True
            and tool.risk_level == "low"
            and tool.qualified_name == f"mcp.{tool.server_name}.{tool.tool_name}"
        )

    def _sanitize_result(
        self,
        result: MCPToolResult,
        server_name: str,
        tool_name: str,
    ) -> MCPToolResult:
        error = self._sanitize_text(result.error)
        metadata = {
            "server": server_name,
            "tool": tool_name,
            "server_name": server_name,
            "tool_name": tool_name,
            "provider": "mcp",
            "read_only": True,
            "risk_level": "low",
        }
        metadata.update(self._sanitize_metadata(result.metadata or {}))

        return MCPToolResult(
            ok=result.ok,
            result=self._sanitize_data(result.result),
            error=error,
            metadata=metadata,
        )

    def _sanitize_data(self, value):
        if isinstance(value, str):
            return self._sanitize_text(value)

        if isinstance(value, list):
            return [
                self._sanitize_data(item)
                for item in value
            ]

        if isinstance(value, dict):
            return {
                key: self._sanitize_data(item)
                for key, item in value.items()
            }

        return value

    def _sanitize_metadata(self, metadata: dict) -> dict:
        blocked = {
            "command",
            "cmd",
            "cwd",
            "env",
            "environment",
            "stderr",
            "stdout",
        }
        return {
            key: value
            for key, value in metadata.items()
            if key not in blocked
        }

    def _sanitize_text(self, text: str | None) -> str | None:
        if text is None:
            return None

        sanitized = text
        for fragment in FORBIDDEN_ERROR_FRAGMENTS:
            sanitized = sanitized.replace(fragment, "[redacted]")
        return sanitized

    def _error(self, message: str) -> MCPToolResult:
        return MCPToolResult(
            ok=False,
            error=self._sanitize_text(message),
            metadata={
                "provider": "mcp",
            },
        )
