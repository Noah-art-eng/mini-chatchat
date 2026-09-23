"""Regression checks for Context selection, deduplication, and rerank candidates."""

import asyncio
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from rag import build_context  # noqa: E402
from chat_service import get_rerank_candidate_count  # noqa: E402
from chat_service import build_streaming_response  # noqa: E402
from chat_service import run_local_kb_chat  # noqa: E402
from chat_service import run_kb_chat  # noqa: E402


def source(source, chunk_id, text):
    """负责 source 的函数职责。"""
    return {"id": chunk_id, "source": source, "chunk_id": chunk_id, "chunk": text}


class ContextAlignmentTest(unittest.TestCase):
    """负责 ContextAlignmentTest 的类职责。"""
    def test_budget_returns_only_chunks_in_prompt(self):
        """负责 test_budget_returns_only_chunks_in_prompt 的函数职责。"""
        results = [
            source("a.txt", 1, "first " * 20),
            source("a.txt", 2, "second " * 20),
        ]
        context, selected = build_context(results, context_token_budget=40, return_results=True)
        self.assertIn("Source 1", context)
        self.assertEqual([item["chunk_id"] for item in selected], [1])

    def test_dedup_removes_same_source_duplicate_and_high_overlap(self):
        """负责 test_dedup_removes_same_source_duplicate_and_high_overlap 的函数职责。"""
        shared = "identical useful text"
        overlap = "A" * 100
        results = [
            source("a.txt", 1, shared),
            source("a.txt", 2, shared),
            source("a.txt", 3, "first tail" + overlap),
            source("a.txt", 4, overlap + "second tail"),
        ]
        _, selected = build_context(results, context_token_budget=None, return_results=True)
        self.assertEqual([item["chunk_id"] for item in selected], [1, 3])

    def test_dedup_keeps_equal_text_from_different_sources(self):
        """负责 test_dedup_keeps_equal_text_from_different_sources 的函数职责。"""
        results = [
            source("a.txt", 1, "shared evidence"),
            source("b.txt", 2, "shared evidence"),
        ]
        _, selected = build_context(results, context_token_budget=None, return_results=True)
        self.assertEqual([item["source"] for item in selected], ["a.txt", "b.txt"])

    def test_rerank_candidate_count_exceeds_final_top_k(self):
        """负责 test_rerank_candidate_count_exceeds_final_top_k 的函数职责。"""
        self.assertEqual(get_rerank_candidate_count(3, 3), 12)
        self.assertEqual(get_rerank_candidate_count(3, 5), 20)

    def test_rerank_receives_more_candidates_than_final_top_k(self):
        """负责 test_rerank_receives_more_candidates_than_final_top_k 的函数职责。"""
        class Service:
            """负责 Service 的类职责。"""
            model = object()

            def __init__(self):
                """负责 __init__ 的函数职责。"""
                self.top_k = None

            def search_docs(self, query, top_k, **_kwargs):
                """负责 search_docs 的函数职责。"""
                self.top_k = top_k
                return [source("a.txt", index, f"chunk {index}") for index in range(1, top_k + 1)]

        service = Service()
        request = SimpleNamespace(
            mode="local_kb", kb_name="default", query="test", top_k=3,
            rerank=True, rerank_top_n=3, score_threshold=0.8,
            metadata_filter=None, source=None, file_name=None,
            conversation_id=None, return_direct=True,
        )
        seen = []

        with (
            patch("chat_service.get_local_kb_service", return_value=service),
            patch("chat_service.create_conversation", return_value=1),
            patch("chat_service.save_message"),
            patch("chat_service.get_conversation_messages", return_value=[]),
            patch("chat_service.rerank_docs", side_effect=lambda _q, docs, _m, top_n: seen.append(len(docs)) or docs[:top_n]),
        ):
            response = run_kb_chat(request, client=None)

        self.assertEqual(service.top_k, 12)
        self.assertEqual(seen, [12])
        self.assertEqual(len(response["sources"]), 3)

    def test_rerank_disabled_keeps_original_retrieval_count(self):
        """负责 test_rerank_disabled_keeps_original_retrieval_count 的函数职责。"""
        class Service:
            """负责 Service 的类职责。"""
            def __init__(self):
                """负责 __init__ 的函数职责。"""
                self.top_k = None

            def search_docs(self, query, top_k, **_kwargs):
                """负责 search_docs 的函数职责。"""
                self.top_k = top_k
                return []

        service = Service()
        request = SimpleNamespace(
            mode="local_kb", kb_name="default", query="test", top_k=3,
            rerank=False, rerank_top_n=3, score_threshold=0.8,
            metadata_filter=None, source=None, file_name=None,
            conversation_id=None, return_direct=True,
        )

        with (
            patch("chat_service.get_local_kb_service", return_value=service),
            patch("chat_service.create_conversation", return_value=1),
            patch("chat_service.save_message"),
            patch("chat_service.get_conversation_messages", return_value=[]),
        ):
            run_kb_chat(request, client=None)

        self.assertEqual(service.top_k, 3)

    def test_streaming_sources_match_selected_context(self):
        """负责 test_streaming_sources_match_selected_context 的函数职责。"""
        results = [
            source("a.txt", 1, "first " * 1200),
            source("a.txt", 2, "second " * 1200),
        ]
        persisted = []

        with patch("chat_service.stream_answer", return_value=iter(["answer"])):
            response = build_streaming_response(
                "question",
                results,
                client=None,
                history=[],
                prompt_name="default",
                save_assistant=lambda answer, sources: persisted.append((answer, sources)),
            )
            payloads = asyncio.run(self._read_stream(response))

        source_event = json.loads(payloads[0].removeprefix("data: "))
        self.assertEqual([item["chunk_id"] for item in source_event["sources"]], [1])
        self.assertEqual([item["chunk_id"] for item in persisted[0][1]], [1])

    def test_non_streaming_sources_match_selected_context(self):
        """负责 test_non_streaming_sources_match_selected_context 的函数职责。"""
        results = [
            source("a.txt", 1, "first " * 1200),
            source("a.txt", 2, "second " * 1200),
        ]
        saved_messages = []
        service = SimpleNamespace(search_docs=lambda *_args, **_kwargs: results)
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_kwargs: SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))]
                    )
                )
            )
        )
        request = SimpleNamespace(
            question="question", conversation_id=None, top_k=3,
            score_threshold=0.8, return_direct=False, stream=False,
            prompt_name="default", model=None, temperature=None, max_tokens=None,
        )

        def save_message(*args, **kwargs):
            """负责 save_message 的函数职责。"""
            saved_messages.append((args, kwargs))
            return len(saved_messages)

        with (
            patch("chat_service.create_conversation", return_value=1),
            patch("chat_service.save_message", side_effect=save_message),
            patch("chat_service.get_conversation_messages", return_value=[]),
        ):
            response = run_local_kb_chat(request, service, client)

        self.assertEqual([item["chunk_id"] for item in response["sources"]], [1])
        self.assertEqual(
            [item["chunk_id"] for item in saved_messages[-1][1]["metadata"]["sources"]],
            [1],
        )

    async def _read_stream(self, response):
        """负责 _read_stream 的函数职责。"""
        payloads = []
        async for chunk in response.body_iterator:
            payloads.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
        return payloads


if __name__ == "__main__":
    unittest.main()
