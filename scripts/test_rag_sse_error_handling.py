"""验证 RAG SSE 失败时不会泄露异常，且客户端结果与持久化内容一致。"""

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


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

TEST_RUNTIME = tempfile.TemporaryDirectory()
atexit.register(TEST_RUNTIME.cleanup)
os.environ["MINI_CHATCHAT_DB_PATH"] = str(Path(TEST_RUNTIME.name) / "mini.db")
os.environ["MINI_CHATCHAT_DATA_ROOT"] = str(Path(TEST_RUNTIME.name) / "data")
os.environ["MINI_CHATCHAT_UPLOADS_DIR"] = str(Path(TEST_RUNTIME.name) / "uploads")


class FakeEmbeddingModel:
    """避免导入 app 时下载真实 Embedding 模型。"""

    def encode(self, texts):
        """返回足够初始化测试知识库的固定向量。"""
        return np.ones((len(texts), 2), dtype="float32")


import services.kb_service as kb_service_module  # noqa: E402

kb_service_module.get_embedding_model = lambda _name: FakeEmbeddingModel()

from api.routes.openai_compat import build_openai_streaming_response  # noqa: E402
from chat_service import RAG_STREAM_ERROR_MESSAGE, build_streaming_response  # noqa: E402


def parse_sse(chunk):
    """从单个测试 SSE chunk 中取出 JSON payload。"""
    text = chunk.decode() if isinstance(chunk, bytes) else chunk
    payload = text.removeprefix("data: ").strip()
    return payload if payload == "[DONE]" else json.loads(payload)


async def collect_stream(response):
    """完整消费测试响应，返回依次发出的 SSE payload。"""
    payloads = []
    async for chunk in response.body_iterator:
        payloads.append(parse_sse(chunk))
    return payloads


class RagSseErrorHandlingTest(unittest.TestCase):
    """覆盖 RAG 流中途失败、首 token 前失败和 OpenAI 兼容适配。"""

    def test_partial_answer_is_persisted_and_internal_error_is_hidden(self):
        """流中途失败时保存已展示的部分回答，并只向客户端发送通用错误。"""
        persisted = []

        def failing_stream(*_args, **_kwargs):
            yield "partial answer"
            raise RuntimeError("secret provider endpoint and credential detail")

        with patch("chat_service.stream_answer", side_effect=failing_stream):
            response = build_streaming_response(
                "question",
                [],
                client=None,
                history=[],
                prompt_name="default",
                save_assistant=lambda answer, sources: persisted.append((answer, sources)) or 7,
            )
            payloads = asyncio.run(collect_stream(response))

        error = next(item for item in payloads if item.get("type") == "error")
        done = next(item for item in payloads if item.get("type") == "done")
        self.assertEqual(error["message"], RAG_STREAM_ERROR_MESSAGE)
        self.assertTrue(error["partial_response"])
        self.assertNotIn("secret provider", json.dumps(payloads))
        self.assertEqual(persisted, [("partial answer", [])])
        self.assertEqual(done["assistant_message_id"], 7)

    def test_failure_before_first_token_persists_displayed_error(self):
        """首 token 前失败时，历史记录保存与前端展示相同的通用错误。"""
        persisted = []

        def failing_stream(*_args, **_kwargs):
            raise RuntimeError("private upstream failure")
            yield  # pragma: no cover

        with patch("chat_service.stream_answer", side_effect=failing_stream):
            response = build_streaming_response(
                "question",
                [],
                client=None,
                history=[],
                prompt_name="default",
                save_assistant=lambda answer, sources: persisted.append((answer, sources)) or 8,
            )
            payloads = asyncio.run(collect_stream(response))

        error = next(item for item in payloads if item.get("type") == "error")
        self.assertFalse(error["partial_response"])
        self.assertEqual(persisted, [(RAG_STREAM_ERROR_MESSAGE, [])])
        self.assertNotIn("private upstream", json.dumps(payloads))

    def test_openai_adapter_propagates_generic_error_without_done(self):
        """OpenAI 兼容流遇到内部 error 时不得伪装成正常完成。"""

        def failing_stream(*_args, **_kwargs):
            yield "partial"
            raise RuntimeError("sensitive sdk exception")

        with patch("chat_service.stream_answer", side_effect=failing_stream):
            internal = build_streaming_response(
                "question",
                [],
                client=None,
                history=[],
                prompt_name="default",
            )
            response = build_openai_streaming_response("chatcmpl-test", "test-model", internal)
            payloads = asyncio.run(collect_stream(response))

        error = next(item for item in payloads if "error" in item)
        self.assertEqual(error["error"]["message"], RAG_STREAM_ERROR_MESSAGE)
        self.assertNotIn("sensitive sdk", json.dumps(payloads))
        self.assertNotIn("[DONE]", payloads)


if __name__ == "__main__":
    unittest.main()
