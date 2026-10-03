from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import threading
from dataclasses import dataclass, field

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
    """描述一个允许启动的 stdio MCP 进程及其安全限制。"""
    server_name: str
    command: str
    args: list[str]
    cwd: str
    env_allowlist: list[str] = field(default_factory=lambda: ["HOME", "PATH"])
    env: dict[str, str] = field(default_factory=dict)
    startup_timeout: float = 20.0
    call_timeout: float = 10.0


class StdioMCPServer:
    """管理一个 stdio MCP 子进程的生命周期和 JSON-RPC 通信。"""
    def __init__(self, config: StdioMCPServerConfig):
        """保存 stdio MCP 配置和并发状态；真正的子进程等到首次调用时再启动。"""
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
        """确保服务已初始化，再返回经过规范化的工具清单。"""
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
        """校验已发现工具及参数后发送 MCP tools/call 请求。"""
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
        """返回外部 MCP 进程、初始化状态和最近错误，供系统页诊断。"""
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
        """终止读写任务和子进程，避免应用关闭时等待卡住的 MCP 初始化。"""
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
        """按需启动子进程并完成 initialize；并发调用共享同一次启动状态。"""
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
        """完成 MCP initialize 握手并发送 initialized 通知，成功后才允许发现工具。"""
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
        """发送带 ID 的 JSON-RPC 请求，并在超时后移除对应等待队列。"""
        # 每个请求 ID 对应一个独立队列。后台 stdout 线程收到响应后按 ID 投递，
        # 因而多个并发 MCP 请求不会取走彼此的结果。
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

        # 外部进程没有按时响应就快速失败。finally 无论成功或超时都移除队列，
        # 避免迟到响应和长期运行的服务不断累积等待对象。
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
        """发送不等待响应的 JSON-RPC 通知。"""
        self._write_message({
            "jsonrpc": JSONRPC_VERSION,
            "method": method,
            "params": params,
        })

    def _write_message(self, payload: dict):
        """把一条 JSON-RPC 消息写入 stdio，并立即刷新到子进程。"""
        process = self._process
        if process is None or process.stdin is None:
            raise RuntimeError("MCP server process is not running")

        body = json.dumps(payload, separators=(",", ":"))
        process.stdin.write(body + "\n")
        process.stdin.flush()

    def _read_stdout_loop(self):
        """持续读取子进程响应，并按请求 ID 投递给对应等待队列。"""
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
        """从 stdout 读取一条 JSON 消息；损坏输出不会作为有效响应。"""
        body = stream.readline()
        if not body:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None

    def _read_stderr_loop(self):
        """保留有限长度的 stderr 尾部，便于诊断又避免无限占用内存。"""
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
        """启动前检查命令、参数、工作目录和环境变量是否在允许范围。"""
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
        """把外部 MCP 工具描述转换成项目统一的 MCPToolSpec。"""
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
        """按工具 schema 检查参数类型和多余字段，再交给外部进程。"""
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
        """对 SQLite MCP 再做只读 SQL 检查，禁止写操作和多语句。"""
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
        """从已发现工具缓存中取规范定义，避免相信 Agent 自带 schema。"""
        specs = self._tool_cache
        if specs is None:
            specs = self.list_tools()

        for spec in specs:
            if spec.tool_name == tool_name:
                return spec
        return None

    def _normalize_tool_result(self, response: dict) -> dict:
        """把外部 content 数组整理成项目统一的结果结构。"""
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
        """生成不包含命令和环境变量的 MCP 结果来源信息。"""
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
        """返回经过清理的稳定 MCP 失败结果。"""
        return MCPToolResult(
            ok=False,
            error=self._sanitize_text(message),
            metadata=self._metadata(tool_name),
        )

    def _sanitize_text(self, text: str | None) -> str | None:
        """截断并清理外部进程文本，避免过大结果进入 Agent 上下文。"""
        if text is None:
            return None

        sanitized = text
        for fragment in FORBIDDEN_TEXT:
            sanitized = sanitized.replace(fragment, "[redacted]")
        return sanitized
