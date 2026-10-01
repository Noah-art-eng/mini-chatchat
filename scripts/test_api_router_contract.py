"""验证 Auth/Agent 路由拆分后仍保持原有 HTTP 契约。"""

import atexit
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

TEST_RUNTIME = tempfile.TemporaryDirectory()
atexit.register(TEST_RUNTIME.cleanup)
os.environ["MINI_CHATCHAT_DB_PATH"] = str(Path(TEST_RUNTIME.name) / "mini.db")
os.environ["MINI_CHATCHAT_DATA_ROOT"] = str(Path(TEST_RUNTIME.name) / "data")
os.environ["MINI_CHATCHAT_UPLOADS_DIR"] = str(Path(TEST_RUNTIME.name) / "uploads")


class FakeEmbeddingModel:
    """避免路由契约测试因模型下载或推理环境而失败。"""

    def encode(self, texts, **_kwargs):
        """返回足以完成空知识库初始化的固定维度向量。"""
        return np.ones((len(texts), 2), dtype="float32")


import services.kb_service as kb_service_module  # noqa: E402

kb_service_module.get_embedding_model = lambda _name: FakeEmbeddingModel()

import app as backend_app  # noqa: E402
from api.routes.agent import router as agent_router  # noqa: E402
from api.routes.auth import router as auth_router  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


EXPECTED_ROUTE_METHODS = {
    "/auth/register": {"POST"},
    "/auth/login": {"POST"},
    "/auth/logout": {"POST"},
    "/auth/logout-all": {"POST"},
    "/auth/refresh": {"POST"},
    "/auth/me": {"GET"},
    "/auth/preferences": {"GET", "PATCH"},
    "/auth/account": {"GET", "PATCH"},
    "/auth/sessions": {"GET"},
    "/auth/sessions/{session_id}": {"DELETE"},
    "/auth/logout-others": {"POST"},
    "/auth/oauth/providers": {"GET"},
    "/auth/oauth/{provider}": {"GET"},
    "/auth/oauth/{provider}/callback": {"GET"},
    "/auth/oauth/link/{provider}": {"POST", "DELETE"},
    "/agent/tools": {"GET"},
    "/agent/tools/{tool_name}/run": {"POST"},
    "/agent/mcp/tools": {"GET"},
    "/agent/mcp/servers": {"GET"},
    "/agent/mcp/servers/{server_name}/shutdown": {"POST"},
    "/agent/mcp/tools/{tool_name}/run": {"POST"},
    "/agent/decide": {"POST"},
    "/agent/run_once": {"POST"},
    "/agent/run": {"POST"},
    "/agent/run_multi": {"POST"},
    "/agent/plan_run": {"POST"},
    "/agent/plan_run_stream": {"POST"},
}


class ApiRouterContractTest(unittest.TestCase):
    """锁定迁移路由的 path、method、Schema 和所属模块。"""

    def test_auth_and_agent_route_methods_are_unchanged(self):
        """防止 include_router 迁移时漏掉路由或改变 HTTP method。"""
        paths = backend_app.app.openapi()["paths"]
        actual = {
            path: {method.upper() for method in operations}
            for path, operations in paths.items()
            if path.startswith(("/auth/", "/agent/"))
        }
        self.assertEqual(actual, EXPECTED_ROUTE_METHODS)

    def test_routes_are_owned_by_new_modules_without_importing_app(self):
        """确认路由已经真正移出 app.py，且新模块没有反向依赖应用入口。"""
        for router, module_name in (
            (auth_router, "api.routes.auth"),
            (agent_router, "api.routes.agent"),
        ):
            for route in router.routes:
                self.assertEqual(route.endpoint.__module__, module_name)

        for relative_path in ("api/routes/auth.py", "api/routes/agent.py"):
            source = (BACKEND_DIR / relative_path).read_text(encoding="utf-8")
            self.assertNotIn("import app", source)
            self.assertNotIn("from app import", source)

    def test_request_schema_contract_is_unchanged(self):
        """锁定迁移路由仍引用原有请求模型和默认校验规则。"""
        schemas = backend_app.app.openapi()["components"]["schemas"]
        agent = schemas["AgentToolCallRequest"]
        self.assertEqual(agent["required"], ["query"])
        self.assertEqual(agent["properties"]["kb_name"]["default"], "default")
        self.assertEqual(agent["properties"]["max_steps"]["default"], 3)

        tool = schemas["ToolRunRequest"]
        self.assertEqual(tool["properties"]["arguments"]["default"], {})

        auth = schemas["AuthEmailPasswordRequest"]
        self.assertEqual(auth["required"], ["email", "password"])
        self.assertNotIn("default", auth["properties"]["display_name"])

        account = schemas["AuthAccountUpdateRequest"]
        self.assertFalse(account["additionalProperties"])

    def test_public_and_protected_route_status_codes_are_unchanged(self):
        """确认拆分没有放宽 Auth、Agent 和 MCP 的访客权限。"""
        with patch("api.routes.agent.list_all_tools", return_value=[]), TestClient(
            backend_app.app
        ) as client:
            self.assertEqual(client.get("/auth/me").status_code, 200)
            self.assertEqual(client.get("/auth/preferences").status_code, 401)
            self.assertEqual(client.get("/agent/tools").status_code, 200)
            self.assertEqual(client.post("/agent/decide", json={"query": "x"}).status_code, 403)
            self.assertEqual(client.get("/agent/mcp/tools").status_code, 403)


if __name__ == "__main__":
    unittest.main()
