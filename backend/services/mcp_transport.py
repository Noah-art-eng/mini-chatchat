from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from .mcp_types import MCPToolResult, MCPToolSpec


JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"
MAX_STDERR_CHARS = 2000
MAX_RESULT_TEXT_CHARS = 12000
SAFE_ENV_KEYS = {
    "HOME",
    "PATH",
    "npm_config_cache",
    "npm_config_prefix",
    "npm_config_offline",
    "npm_config_prefer_offline",
    "SQLITE_DB_PATH",
}
ALLOWED_COMMANDS = {"npx", "/opt/homebrew/bin/npx", "/usr/local/bin/npx"}
ALLOWED_PACKAGES = {
    "@modelcontextprotocol/server-filesystem",
    "mcp-server-filesystem",
    "mcp-server-sqlite",
}
READONLY_TOOLS_BY_SERVER = {
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
WRITE_TOOL_MARKERS = (
    "write",
    "edit",
    "delete",
    "remove",
    "move",
    "rename",
    "create",
    "upload",
    "download",
    "shell",
    "command",
)
FORBIDDEN_SQL = re.compile(
    r"\b("
    r"alter|attach|create|delete|detach|drop|execute|insert|load_extension|"
    r"pragma\s+(?!table_info\b)|reindex|replace|truncate|update|vacuum"
    r")\b",
    flags=re.IGNORECASE,
)
FORBIDDEN_TEXT = (
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "invalid_api_key",
    "OpenAI 401",
    "MCP command",
    "environment",
    "stderr",
)


@dataclass(frozen=True)
class StdioMCPServerConfig:
    server_name: str
    command: str
    args: list[str]
    cwd: str
    env_allowlist: list[str] = field(default_factory=lambda: ["HOME", "PATH"])
    env: dict[str, str] = field(default_factory=dict)
    startup_timeout: float = 20.0
    call_timeout: float = 10.0


class StdioMCPServer:
    def __init__(self, config: StdioMCPServerConfig):
        self.config = config
        self.name = config.server_name
        self._process: subprocess.Popen | None = None
        self._reader_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._responses: dict[int, queue.Queue] = {}
        self._notifications: queue.Queue = queue.Queue()
        self._lock = threading.RLock()
        self._next_id = 1
        self._initialized = False
        self._last_error: str | None = None
        self._stderr_tail = ""
        self._tool_cache: list[MCPToolSpec] | None = None

    def list_tools(self) -> list[MCPToolSpec]:
        self._ensure_started()
        response = self._request("tools/list", {}, timeout=self.config.call_timeout)
        tools = response.get("tools")
        if not isinstance(tools, list):
            raise RuntimeError("MCP tools/list returned invalid tools")

        specs = []
        for tool in tools:
            spec = self._normalize_tool(tool)
            if spec is not None:
                specs.append(spec)

        self._tool_cache = specs
        return specs

    def call_tool(self, tool_name: str, arguments: dict) -> MCPToolResult:
        self._ensure_started()
        spec = self._get_cached_tool(tool_name)
        if spec is None:
            return self._error(
                f"MCP tool not allowed or not found: {self.name}.{tool_name}",
                tool_name,
            )

        validation_error = self._validate_tool_arguments(tool_name, arguments or {})
        if validation_error:
            return self._error(validation_error, tool_name)

        try:
            response = self._request(
                "tools/call",
                {
                    "name": tool_name,
                    "arguments": arguments or {},
                },
                timeout=self.config.call_timeout,
            )
        except TimeoutError:
            return self._error("MCP tool timed out", tool_name)
        except Exception:
            return self._error("MCP tool failed", tool_name)

        if response.get("isError") is True:
            return self._error("MCP tool returned an error", tool_name)

        return MCPToolResult(
            ok=True,
            result=self._normalize_tool_result(response),
            metadata=self._metadata(tool_name),
        )

    def status(self) -> dict:
        with self._lock:
            running = self._process is not None and self._process.poll() is None
            initialized = self._initialized and running
            tool_count = len(self._tool_cache or []) if initialized else 0
            error = self._sanitize_text(self._last_error)

        data = {
            "server": self.name,
            "enabled": True,
            "provider": "mcp",
            "transport": "stdio",
            "running": running,
            "initialized": initialized,
            "tool_count": tool_count,
        }
        if error:
            data["error"] = error
        return data

    def shutdown(self) -> dict:
        with self._lock:
            process = self._process
            self._process = None
            self._initialized = False
            self._tool_cache = None

        if process is None:
            return self.status()

        if process.poll() is None:
            try:
                self._send_notification("notifications/cancelled", {})
            except Exception:
                pass
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)

        return self.status()

    def _ensure_started(self):
        with self._lock:
            if self._process is not None and self._process.poll() is None and self._initialized:
                return

            self._validate_config()
            env = {
                key: os.environ[key]
                for key in self.config.env_allowlist
                if key in SAFE_ENV_KEYS and key in os.environ
            }
            home = env.get("HOME", os.path.expanduser("~"))
            env.setdefault("npm_config_cache", os.path.join(home, ".npm"))
            env.setdefault("npm_config_prefix", os.path.join(home, ".npm-global"))
            env.setdefault("npm_config_offline", "true")
            env.setdefault("npm_config_prefer_offline", "true")
            for key, value in self.config.env.items():
                if key in SAFE_ENV_KEYS:
                    env[key] = value
            self._process = subprocess.Popen(
                [self.config.command, *self.config.args],
                cwd=self.config.cwd,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
            )
            self._responses = {}
            self._notifications = queue.Queue()
            self._last_error = None
            self._stderr_tail = ""
            self._initialized = False
            self._reader_thread = threading.Thread(
                target=self._read_stdout_loop,
                name=f"mcp-{self.name}-stdout",
                daemon=True,
            )
            self._stderr_thread = threading.Thread(
                target=self._read_stderr_loop,
                name=f"mcp-{self.name}-stderr",
                daemon=True,
            )
            self._reader_thread.start()
            self._stderr_thread.start()

        try:
            self._initialize()
        except Exception as exc:
            self._last_error = str(exc)
            self.shutdown()
            raise

    def _initialize(self):
        response = self._request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "mini-chatchat",
                    "version": "0.1.0",
                },
            },
            timeout=self.config.startup_timeout,
        )
        if not isinstance(response, dict):
            raise RuntimeError("MCP initialize returned invalid response")

        self._send_notification("notifications/initialized", {})
        with self._lock:
            self._initialized = True

    def _request(self, method: str, params: dict, timeout: float) -> dict:
        with self._lock:
            request_id = self._next_id
            self._next_id += 1
            response_queue: queue.Queue = queue.Queue(maxsize=1)
            self._responses[request_id] = response_queue
            process = self._process

        if process is None or process.stdin is None or process.poll() is not None:
            raise RuntimeError("MCP server process is not running")

        payload = {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "method": method,
            "params": params,
        }
        self._write_message(payload)

        try:
            message = response_queue.get(timeout=timeout)
        except queue.Empty as exc:
            raise TimeoutError(f"MCP request timed out: {method}") from exc
        finally:
            with self._lock:
                self._responses.pop(request_id, None)

        if not isinstance(message, dict):
            raise RuntimeError("MCP response is invalid")

        error = message.get("error")
        if error:
            raise RuntimeError("MCP request failed")

        result = message.get("result")
        if not isinstance(result, dict):
            return {}
        return result

    def _send_notification(self, method: str, params: dict):
        self._write_message({
            "jsonrpc": JSONRPC_VERSION,
            "method": method,
            "params": params,
        })

    def _write_message(self, payload: dict):
        process = self._process
        if process is None or process.stdin is None:
            raise RuntimeError("MCP server process is not running")

        body = json.dumps(payload, separators=(",", ":"))
        process.stdin.write(body + "\n")
        process.stdin.flush()

    def _read_stdout_loop(self):
        process = self._process
        if process is None or process.stdout is None:
            return

        while process.poll() is None:
            try:
                message = self._read_message(process.stdout)
            except Exception:
                break

            if not isinstance(message, dict):
                continue

            request_id = message.get("id")
            if isinstance(request_id, int):
                with self._lock:
                    response_queue = self._responses.get(request_id)
                if response_queue is not None:
                    response_queue.put(message)
            else:
                self._notifications.put(message)

    def _read_message(self, stream) -> dict | None:
        body = stream.readline()
        if not body:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None

    def _read_stderr_loop(self):
        process = self._process
        if process is None or process.stderr is None:
            return

        while process.poll() is None:
            chunk = process.stderr.readline()
            if not chunk:
                break
            text = chunk
            with self._lock:
                self._stderr_tail = (self._stderr_tail + text)[-MAX_STDERR_CHARS:]

    def _validate_config(self):
        command = self.config.command
        if command not in ALLOWED_COMMANDS:
            raise ValueError("MCP server command is not allowed")

        if not self.config.args or self.config.args[0] != "-y":
            raise ValueError("MCP server arguments are not allowed")

        package_args = [
            arg
            for arg in self.config.args
            if arg in ALLOWED_PACKAGES
        ]
        if len(package_args) != 1:
            raise ValueError("MCP server package is not allowed")

        package_name = package_args[0]
        if self.name == "sqlite" and package_name != "mcp-server-sqlite":
            raise ValueError("MCP server package is not allowed")
        if self.name == "filesystem_stdio" and package_name == "mcp-server-sqlite":
            raise ValueError("MCP server package is not allowed")

        cwd = os.path.abspath(self.config.cwd)
        if cwd != self.config.cwd or not os.path.isdir(cwd):
            raise ValueError("MCP server cwd is not allowed")

        for arg in self.config.args:
            if any(marker in arg for marker in [";", "|", "&", "$", "`", "\n"]):
                raise ValueError("MCP server arguments are not allowed")

        if self.name == "sqlite":
            db_paths = [
                os.path.abspath(arg)
                for arg in self.config.args
                if arg.endswith(".db")
            ]
            env_db_path = self.config.env.get("SQLITE_DB_PATH")
            if env_db_path:
                db_paths.append(os.path.abspath(env_db_path))
            expected_db = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "mini.db")
            )
            if db_paths != [expected_db]:
                raise ValueError("MCP server database path is not allowed")

    def _normalize_tool(self, tool: dict) -> MCPToolSpec | None:
        name = tool.get("name")
        if not isinstance(name, str) or not name:
            return None

        allowed_tools = READONLY_TOOLS_BY_SERVER.get(self.name, set())
        if name not in allowed_tools:
            return None

        lowered = name.lower()
        if any(marker in lowered for marker in WRITE_TOOL_MARKERS):
            return None

        input_schema = tool.get("inputSchema") or tool.get("input_schema") or {}
        if not isinstance(input_schema, dict):
            input_schema = {}

        description = tool.get("description")
        if not isinstance(description, str):
            description = f"Read-only MCP filesystem tool: {name}."

        return MCPToolSpec(
            server_name=self.name,
            tool_name=name,
            qualified_name=f"mcp.{self.name}.{name}",
            description=description,
            input_schema=input_schema,
            read_only=True,
            risk_level="low",
        )

    def _validate_tool_arguments(self, tool_name: str, arguments: dict) -> str | None:
        if self.name != "sqlite":
            return None

        if tool_name == "query":
            sql = arguments.get("sql")
            if not isinstance(sql, str):
                return "sql must be a string"

            return self._validate_sqlite_query(sql)

        if tool_name == "describe-table":
            table_name = arguments.get("tableName")
            if not isinstance(table_name, str) or not table_name.strip():
                return "tableName must be a non-empty string"
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table_name.strip()):
                return "tableName is not allowed"

        return None

    def _validate_sqlite_query(self, sql: str) -> str | None:
        stripped = sql.strip()
        if not stripped:
            return "sql is required"

        if ";" in stripped.rstrip(";"):
            return "only one SQL statement is allowed"

        stripped = stripped.rstrip(";").strip()
        if not re.match(r"^(select|pragma\s+table_info)\b", stripped, flags=re.IGNORECASE):
            return "only SELECT or PRAGMA table_info statements are allowed"

        if FORBIDDEN_SQL.search(stripped):
            return "write or unsafe SQL is not allowed"

        return None

    def _get_cached_tool(self, tool_name: str) -> MCPToolSpec | None:
        specs = self._tool_cache
        if specs is None:
            specs = self.list_tools()

        for spec in specs:
            if spec.tool_name == tool_name:
                return spec
        return None

    def _normalize_tool_result(self, response: dict) -> dict:
        content = response.get("content")
        texts = []
        structured = response.get("structuredContent")

        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    texts.append(item["text"])

        text = "\n".join(texts)
        if len(text) > MAX_RESULT_TEXT_CHARS:
            text = text[:MAX_RESULT_TEXT_CHARS]

        result = {
            "content": content,
            "text": text,
            "truncated": len("\n".join(texts)) > MAX_RESULT_TEXT_CHARS,
        }
        if isinstance(structured, dict):
            result["structuredContent"] = structured
        return result

    def _metadata(self, tool_name: str) -> dict:
        return {
            "server": self.name,
            "tool": tool_name,
            "server_name": self.name,
            "tool_name": tool_name,
            "provider": "mcp",
            "transport": "stdio",
            "read_only": True,
            "risk_level": "low",
        }

    def _error(self, message: str, tool_name: str) -> MCPToolResult:
        return MCPToolResult(
            ok=False,
            error=self._sanitize_text(message),
            metadata=self._metadata(tool_name),
        )

    def _sanitize_text(self, text: str | None) -> str | None:
        if text is None:
            return None

        sanitized = text
        for fragment in FORBIDDEN_TEXT:
            sanitized = sanitized.replace(fragment, "[redacted]")
        return sanitized
