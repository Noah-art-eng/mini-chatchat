"""验证 Phase C 分块兼容性、Embedding batching 和 FAISS 顺序。"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import faiss
import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import rag  # noqa: E402
from services import kb_service as kb_service_module  # noqa: E402


class RecordingEmbeddingModel:
    """记录每次 encode 收到的文本，并返回可预测的二维向量。"""

    def __init__(self):
        self.calls = []

    def encode(self, texts):
        """按输入文本生成稳定向量，使批次和检索顺序都可断言。"""
        batch = list(texts)
        self.calls.append(batch)
        return np.asarray(
            [
                [
                    float(len(text)),
                    float(sum(ord(char) for char in text) % 997),
                ]
                for text in batch
            ],
            dtype="float32",
        )


class RecordingIndex:
    """记录 FAISS add 的批次，并按追加顺序保存向量。"""

    def __init__(self, dimension):
        self.dimension = dimension
        self.add_calls = []
        self.ntotal = 0

    def add(self, vectors):
        """保存每批向量副本，避免测试结果受后续数组复用影响。"""
        copied = np.asarray(vectors, dtype="float32").copy()
        self.add_calls.append(copied)
        self.ntotal += len(copied)


class RagIndexBatchingTest(unittest.TestCase):
    """验证索引阶段降低临时副本后仍保持原有 chunk 和检索语义。"""

    def test_streamed_chunks_match_legacy_split_exactly(self):
        """同一批文件的新旧路径必须生成完全相同的文本、顺序、来源和 chunk_id。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "alpha.txt").write_text("abcdefghij", encoding="utf-8")
            (root / "beta.txt").write_text("中文🙂XYZ", encoding="utf-8")
            (root / "ignored.md").write_text("ignored", encoding="utf-8")

            legacy = rag.split_documents(
                rag.load_documents(root),
                chunk_size=4,
                overlap=1,
            )
            streamed = rag.load_and_split_documents(
                root,
                chunk_size=4,
                overlap=1,
            )

            self.assertEqual(streamed, legacy)

    def test_chunking_edge_cases_match_legacy_behavior(self):
        """空目录、空文件、单 chunk 和边界长度都不能改变旧切分结果。"""
        cases = {
            "empty_directory": None,
            "empty_file": "",
            "single": "abc",
            "exact": "abcd",
            "overlap_tail": "abcdefg",
        }

        for name, content in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                if content is not None:
                    (root / f"{name}.txt").write_text(content, encoding="utf-8")

                legacy = rag.split_documents(
                    rag.load_documents(root),
                    chunk_size=4,
                    overlap=1,
                )
                streamed = rag.load_and_split_documents(
                    root,
                    chunk_size=4,
                    overlap=1,
                )

                self.assertEqual(streamed, legacy)

    def test_embedding_and_faiss_add_are_batched_in_order(self):
        """五个 chunk、batch size 2 应触发三次 encode/add，并保持向量插入顺序。"""
        chunks = [
            {"text": f"chunk-{index}", "source": "a.txt", "chunk_id": index + 1}
            for index in range(5)
        ]
        model = RecordingEmbeddingModel()
        recording_index = RecordingIndex(2)

        with patch.object(
            rag.faiss,
            "IndexFlatL2",
            return_value=recording_index,
        ):
            index, vectors = rag.build_faiss_index(
                chunks,
                model,
                batch_size=2,
            )

        self.assertIs(index, recording_index)
        self.assertIsNone(vectors)
        self.assertEqual([len(call) for call in model.calls], [2, 2, 1])
        self.assertTrue(all(len(call) <= 2 for call in model.calls))
        self.assertEqual([len(batch) for batch in index.add_calls], [2, 2, 1])
        self.assertEqual(index.ntotal, len(chunks))

        inserted = np.concatenate(index.add_calls, axis=0)
        expected = RecordingEmbeddingModel().encode(
            [chunk["text"] for chunk in chunks]
        )
        np.testing.assert_array_equal(inserted, expected)

    def test_exact_batch_and_batch_plus_one_have_expected_call_counts(self):
        """批次数量边界必须是一次和两次，不能退回全量 encode。"""
        for chunk_count, expected_calls in ((1, [1]), (3, [3]), (4, [3, 1])):
            with self.subTest(chunk_count=chunk_count):
                chunks = [
                    {
                        "text": f"text-{index}",
                        "source": "a.txt",
                        "chunk_id": index + 1,
                    }
                    for index in range(chunk_count)
                ]
                model = RecordingEmbeddingModel()

                index, vectors = rag.build_faiss_index(
                    chunks,
                    model,
                    batch_size=3,
                )

                self.assertIsNone(vectors)
                self.assertEqual([len(call) for call in model.calls], expected_calls)
                self.assertEqual(index.ntotal, chunk_count)

    def test_batched_index_matches_legacy_retrieval_order_and_distances(self):
        """固定向量下，分批 add 与旧的一次 add 必须返回相同排序和距离。"""
        chunks = [
            {"text": text, "source": "a.txt", "chunk_id": index + 1}
            for index, text in enumerate(("alpha", "beta", "gamma", "delta", "epsilon"))
        ]
        texts = [chunk["text"] for chunk in chunks]
        legacy_model = RecordingEmbeddingModel()
        legacy_vectors = np.asarray(legacy_model.encode(texts), dtype="float32")
        legacy_index = faiss.IndexFlatL2(legacy_vectors.shape[1])
        legacy_index.add(legacy_vectors)

        batched_index, _ = rag.build_faiss_index(
            chunks,
            RecordingEmbeddingModel(),
            batch_size=2,
        )
        query_vector = RecordingEmbeddingModel().encode(["alphabet"])

        legacy_distances, legacy_indexes = legacy_index.search(query_vector, 5)
        batched_distances, batched_indexes = batched_index.search(query_vector, 5)

        np.testing.assert_array_equal(batched_indexes, legacy_indexes)
        np.testing.assert_allclose(batched_distances, legacy_distances, rtol=1e-6)

    def test_kb_build_uses_direct_file_chunking_without_full_documents(self):
        """KB rebuild 不应先填充 self.documents 再从完整正文集合生成 chunks。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "content.txt").write_text("abcdefgh", encoding="utf-8")
            service = kb_service_module.MiniKBService.__new__(
                kb_service_module.MiniKBService
            )
            service.kb_name = "test"
            service.content_path = str(root)
            service.chunk_size = 4
            service.chunk_overlap = 1
            service.model = RecordingEmbeddingModel()
            service.documents = [{"text": "stale", "source": "stale.txt"}]
            service.chunks = []
            service.index = None
            service.vectors = None
            service._bm25_docs = []
            service._bm25_doc_freqs = {}
            service._bm25_idf = {}
            service._bm25_avgdl = 0.0

            with patch.object(
                kb_service_module,
                "load_documents",
                side_effect=AssertionError("build_index loaded all documents"),
            ):
                service.build_index()

            self.assertEqual(service.documents, [])
            self.assertEqual([chunk["text"] for chunk in service.chunks], [
                "abcd",
                "defg",
                "gh",
            ])
            self.assertEqual(service.index.ntotal, len(service.chunks))
            self.assertIsNone(service.vectors)


if __name__ == "__main__":
    unittest.main()
