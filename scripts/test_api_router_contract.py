"""验证 Auth、Agent 与 Conversation 路由拆分后仍保持原有 HTTP 契约。"""

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
os.environ["OPENAI_API_KEY"] = ""
os.environ["DEEPSEEK_API_KEY"] = ""


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
from api.routes.conversations import router as conversation_router  # noqa: E402
from api.routes.openai_compat import create_openai_compat_router  # noqa: E402
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

EXPECTED_CONVERSATION_OPERATIONS = {
    ("/chat/feedback", "post"): {
        "operation_id": "chat_feedback_chat_feedback_post",
        "request_schema": "#/components/schemas/FeedbackRequest",
        "response_schema": {},
    },
    ("/conversations", "get"): {
        "operation_id": "get_conversations_conversations_get",
        "request_schema": None,
        "response_schema": {},
    },
    ("/conversations/{conversation_id}/messages", "get"): {
        "operation_id": (
            "get_conversation_history_"
            "conversations__conversation_id__messages_get"
        ),
        "request_schema": None,
        "response_schema": {},
    },
    ("/conversations/{conversation_id}", "patch"): {
        "operation_id": (
            "update_conversation_conversations__conversation_id__patch"
        ),
        "request_schema": "#/components/schemas/ConversationUpdateRequest",
        "response_schema": {},
    },
    ("/conversations/{conversation_id}", "delete"): {
        "operation_id": (
            "remove_conversation_conversations__conversation_id__delete"
        ),
        "request_schema": None,
        "response_schema": {},
    },
}

EXPECTED_CONVERSATION_ROUTE_METHODS = {
    "/chat/feedback": {"POST"},
    "/conversations": {"GET"},
    "/conversations/{conversation_id}/messages": {"GET"},
    "/conversations/{conversation_id}": {"PATCH", "DELETE"},
}

EXPECTED_OPENAI_COMPAT_OPERATION = {
    "operation_id": "chat_completions_chat_completions_post",
    "request_schema": "#/components/schemas/OpenAIChatCompletionRequest",
    "response_schema": {},
    "validation_schema": "#/components/schemas/HTTPValidationError",
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
            (conversation_router, "api.routes.conversations"),
        ):
            for route in router.routes:
                self.assertEqual(route.endpoint.__module__, module_name)

        for relative_path in (
            "api/routes/auth.py",
            "api/routes/agent.py",
            "api/routes/conversations.py",
        ):
            source = (BACKEND_DIR / relative_path).read_text(encoding="utf-8")
            self.assertNotIn("import app", source)
            self.assertNotIn("from app import", source)

    def test_conversation_route_contract_is_unchanged(self):
        """锁定 Conversation 路由迁移前后的 method、operation 和 Schema。"""
        paths = backend_app.app.openapi()["paths"]
        actual_methods = {
            path: {method.upper() for method in paths[path]}
            for path in EXPECTED_CONVERSATION_ROUTE_METHODS
        }
        self.assertEqual(actual_methods, EXPECTED_CONVERSATION_ROUTE_METHODS)

        for (path, method), expected in EXPECTED_CONVERSATION_OPERATIONS.items():
            operation = paths[path][method]
            request_schema = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
                .get("$ref")
            )
            response_schema = operation["responses"]["200"]["content"][
                "application/json"
            ]["schema"]

            self.assertEqual(operation["operationId"], expected["operation_id"])
            self.assertEqual(request_schema, expected["request_schema"])
            self.assertEqual(response_schema, expected["response_schema"])

    def test_openai_compat_route_contract_is_unchanged(self):
        """锁定 Chat Completions 的 method、operation 和 Schema。"""
        operation = backend_app.app.openapi()["paths"]["/chat/completions"]
        self.assertEqual(set(operation), {"post"})

        post = operation["post"]
        request_schema = post["requestBody"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        response_schema = post["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        validation_schema = post["responses"]["422"]["content"][
            "application/json"
        ]["schema"]["$ref"]

        self.assertEqual(
            post["operationId"],
            EXPECTED_OPENAI_COMPAT_OPERATION["operation_id"],
        )
        self.assertEqual(
            request_schema,
            EXPECTED_OPENAI_COMPAT_OPERATION["request_schema"],
        )
        self.assertEqual(
            response_schema,
            EXPECTED_OPENAI_COMPAT_OPERATION["response_schema"],
        )
        self.assertEqual(
            validation_schema,
            EXPECTED_OPENAI_COMPAT_OPERATION["validation_schema"],
        )

        route = create_openai_compat_router(object()).routes[0]
        self.assertEqual(route.endpoint.__module__, "api.routes.openai_compat")

        source = (BACKEND_DIR / "api/routes/openai_compat.py").read_text(
            encoding="utf-8"
        )
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
