"""验证 OpenAI-compatible Router 的 JSON、SSE 与错误协议。"""

import asyncio
import atexit
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.responses import StreamingResponse


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

TEST_RUNTIME = tempfile.TemporaryDirectory()
atexit.register(TEST_RUNTIME.cleanup)
os.environ["MINI_CHATCHAT_DB_PATH"] = str(Path(TEST_RUNTIME.name) / "mini.db")
os.environ["MINI_CHATCHAT_DATA_ROOT"] = str(Path(TEST_RUNTIME.name) / "data")
os.environ["MINI_CHATCHAT_UPLOADS_DIR"] = str(Path(TEST_RUNTIME.name) / "uploads")


class FakeEmbeddingModel:
    """避免 Router 测试依赖真实 Embedding 模型。"""

    def encode(self, texts, **_kwargs):
        """返回足以完成测试初始化的固定向量。"""
        return np.ones((len(texts), 2), dtype="float32")


import services.kb_service as kb_service_module  # noqa: E402

kb_service_module.get_embedding_model = lambda _name: FakeEmbeddingModel()

import app as backend_app  # noqa: E402
from api.routes.openai_compat import (  # noqa: E402
    build_openai_static_streaming_response,
    build_openai_streaming_response,
)
from chat_service import RAG_STREAM_ERROR_MESSAGE  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


async def collect_stream(response):
    """完整读取测试 SSE 响应，保留实际 wire text。"""
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    return chunks


def internal_stream(*events):
    """构造 RAG 内部 SSE，隔离真实模型和网络调用。"""
    async def event_stream():
        for event in events:
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class OpenAICompatRouterTest(unittest.TestCase):
    """锁定 OpenAI-compatible endpoint 的公开响应协议。"""

    def test_non_streaming_endpoint_response_is_unchanged(self):
        """非流式请求继续返回 OpenAI choice 及 Mini ChatChat 扩展字段。"""
        result = {
            "answer": "final answer",
            "sources": [{"source": "guide.txt"}],
            "assistant_message_id": 19,
        }

        with patch("api.routes.openai_compat.run_kb_chat", return_value=result), TestClient(
            backend_app.app
        ) as client:
            response = client.post(
                "/chat/completions",
                json={
                    "model": "test-model",
                    "messages": [{"role": "user", "content": "question"}],
                },
            )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload.pop("id").startswith("chatcmpl-"))
        self.assertEqual(payload, {
            "object": "chat.completion",
            "model": "test-model",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "final answer"},
                "finish_reason": "stop",
            }],
            "sources": [{"source": "guide.txt"}],
            "assistant_message_id": 19,
        })

    def test_invalid_extra_body_keeps_validation_status(self):
        """内部 KB 请求参数越界时仍由兼容入口返回 HTTP 422。"""
        with patch("api.routes.openai_compat.run_kb_chat") as run_kb_chat, TestClient(
            backend_app.app
        ) as client:
            response = client.post(
                "/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "question"}],
                    "extra_body": {"top_k": 0},
                },
            )

        self.assertEqual(response.status_code, 422)
        run_kb_chat.assert_not_called()

    def test_streaming_adapter_preserves_token_and_done_wire_format(self):
        """正常 RAG stream 仍转换为 OpenAI chunk，并以 `[DONE]` 结束。"""
        internal = internal_stream(
            {"type": "sources", "sources": [{"source": "ignored.txt"}]},
            {"type": "token", "content": "hello"},
            {"type": "done", "assistant_message_id": 3},
        )
        response = build_openai_streaming_response(
            "chatcmpl-test",
            "test-model",
            internal,
        )
        chunks = asyncio.run(collect_stream(response))

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[1], "data: [DONE]\n\n")
        token = json.loads(chunks[0].removeprefix("data: ").strip())
        self.assertEqual(token, {
            "id": "chatcmpl-test",
            "object": "chat.completion.chunk",
            "model": "test-model",
            "choices": [{
                "delta": {"content": "hello"},
                "index": 0,
                "finish_reason": None,
            }],
        })

    def test_streaming_adapter_preserves_generic_error_without_done(self):
        """RAG error 继续使用稳定错误 payload，且不能发送成功 `[DONE]`。"""
        internal = internal_stream(
            {"type": "token", "content": "partial"},
            {"type": "error", "message": "private provider error"},
            {"type": "done", "assistant_message_id": 4},
        )
        response = build_openai_streaming_response(
            "chatcmpl-test",
            "test-model",
            internal,
        )
        chunks = asyncio.run(collect_stream(response))

        self.assertNotIn("[DONE]", "".join(chunks))
        self.assertNotIn("private provider error", "".join(chunks))
        error = json.loads(chunks[1].removeprefix("data: ").strip())
        self.assertEqual(error, {
            "error": {
                "message": RAG_STREAM_ERROR_MESSAGE,
                "type": "server_error",
                "code": "rag_stream_error",
            }
        })

    def test_static_stream_preserves_chunk_then_done(self):
        """同步 RAG 结果在 stream 模式下仍输出单个 chunk 和 `[DONE]`。"""
        response = build_openai_static_streaming_response(
            "chatcmpl-test",
            "test-model",
            {"answer": "static answer"},
        )
        chunks = asyncio.run(collect_stream(response))

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[1], "data: [DONE]\n\n")
        token = json.loads(chunks[0].removeprefix("data: ").strip())
        self.assertEqual(token["choices"][0]["delta"]["content"], "static answer")


if __name__ == "__main__":
    unittest.main()
