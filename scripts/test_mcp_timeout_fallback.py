"""验证外部 stdio MCP 不可用时，工具发现能够快速降级。"""

import sys
import time
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from services.mcp_client import DemoMCPServer, MCPClient  # noqa: E402
from services.mcp_transport import (  # noqa: E402
    StdioMCPServer,
    StdioMCPServerConfig,
)


class MCPTimeoutFallbackTest(unittest.TestCase):
    """覆盖外部 MCP 初始化 timeout、fallback 与子进程清理。"""

    def make_hanging_server(self, name: str) -> StdioMCPServer:
        """创建不会响应 initialize 的本地进程，不依赖真实 npx/MCP 包。"""
        class TestStdioMCPServer(StdioMCPServer):
            def _validate_config(self):
                """测试只绕过命令 allowlist，生产安全策略保持原样。"""

        return TestStdioMCPServer(
            StdioMCPServerConfig(
                server_name=name,
                command=sys.executable,
                args=["-c", "import time; time.sleep(60)"],
                cwd=str(ROOT_DIR),
                startup_timeout=0.4,
                call_timeout=0.4,
            )
        )

    def test_default_stdio_startup_timeout_is_bounded(self):
        """默认外部 MCP 初始化不能让普通 Tool API 等待几十秒。"""
        client = MCPClient()
        stdio_servers = [
            server
            for server in client.servers.values()
            if isinstance(server, StdioMCPServer)
        ]
        self.assertTrue(stdio_servers)
        self.assertTrue(
            all(server.config.startup_timeout <= 5 for server in stdio_servers)
        )

    def test_unavailable_stdio_servers_preserve_local_mcp_tools(self):
        """外部 MCP 超时后仍返回 demo 工具，并关闭失败的子进程。"""
        filesystem = self.make_hanging_server("filesystem_stdio")
        sqlite = self.make_hanging_server("sqlite")
        client = MCPClient({
            "demo": DemoMCPServer(),
            "filesystem_stdio": filesystem,
            "sqlite": sqlite,
        })

        started_at = time.monotonic()
        tools = client.discover_tools()
        elapsed = time.monotonic() - started_at

        self.assertIn("mcp.demo.echo", {tool.qualified_name for tool in tools})
        self.assertLess(elapsed, 0.7)
        self.assertFalse(filesystem.status()["running"])
        self.assertFalse(sqlite.status()["running"])


if __name__ == "__main__":
    unittest.main()
