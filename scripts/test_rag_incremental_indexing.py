"""验证 Phase E 只为变化文件生成向量，并保持现有索引契约。"""

import json
import os
import sys
import tempfile
import threading
import unittest
import zipfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import faiss
import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import rag  # noqa: E402
from services import kb_import_export_service as import_service  # noqa: E402
from services import kb_service as kb_module  # noqa: E402


class RecordingEmbeddingModel:
    """记录真实 encode 输入，并为每段文本生成稳定的三维向量。"""

    def __init__(self, dimension=3):
        self.dimension = dimension
        self.calls = []

    def get_sentence_embedding_dimension(self):
        """返回 metadata compatibility 检查使用的模型维度。"""
        return self.dimension

    def encode(self, texts):
        """生成可从文本稳定复算的 float32 向量。"""
        batch = list(texts)
        self.calls.append(batch)
        rows = []
        for text in batch:
            base = [
                float(len(text)),
                float(sum(ord(char) for char in text) % 997),
                float(sum((i + 1) * ord(char) for i, char in enumerate(text)) % 991),
            ]
            rows.append(base[:self.dimension])
        return np.asarray(rows, dtype="float32")

    def clear(self):
        """清空调用记录，使断言只统计当前 mutation。"""
        self.calls.clear()

    @property
    def encoded_texts(self):
        """按调用顺序展开所有批次。"""
        return [text for batch in self.calls for text in batch]


class IncrementalIndexingTest(unittest.TestCase):
    """在临时 content/vector_store 中验证增量索引，不访问真实 KB。"""

    def setUp(self):
        """每个测试使用独立目录和 deterministic fake embedding。"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        """释放当前测试的隔离文件。"""
        self.temp_dir.cleanup()

    def make_service(self, model=None, chunk_size=3, overlap=0):
        """构造不触发真实模型、用户目录或数据库初始化的 KB service。"""
        service = kb_module.MiniKBService.__new__(kb_module.MiniKBService)
        service.kb_name = "phase-e"
        service.user_id = 1
        service.embedding_model_name = "fake-v1"
        service.chunk_size = chunk_size
        service.chunk_overlap = overlap
        service.mutation_lock = threading.RLock()
        service.root_path = str(self.root)
        service.kb_path = str(self.root / "phase-e")
        service.content_path = str(Path(service.kb_path) / "content")
        service.upload_path = str(Path(service.kb_path) / "uploads")
        service.vector_store_path = str(Path(service.kb_path) / "vector_store")
        for path in (service.content_path, service.upload_path, service.vector_store_path):
            Path(path).mkdir(parents=True, exist_ok=True)
        service.model = model or RecordingEmbeddingModel()
        service.documents = []
        service.chunks = []
        service.index = None
        service.vectors = None
        service.vector_metadata = None
        service._bm25_docs = []
        service._bm25_doc_freqs = Counter()
        service._bm25_idf = {}
        service._bm25_avgdl = 0.0
        return service

    def write(self, service, filename, text):
        """写入测试 content，模拟 Phase B 已完成的解析结果。"""
        Path(service.content_path, filename).write_text(text, encoding="utf-8")

    def create_snapshot(self, files, *, chunk_size=3, overlap=0):
        """创建带 Phase E metadata 的初始完整快照，并清空基线调用记录。"""
        model = RecordingEmbeddingModel()
        service = self.make_service(model, chunk_size=chunk_size, overlap=overlap)
        for filename, text in files.items():
            self.write(service, filename, text)
        service.build_index()
        service.save_vector_store()
        model.clear()
        return service, model

    def vectors(self, service):
        """按 FAISS position 取回当前全部向量。"""
        if service.index is None:
            return np.empty((0, service.model.dimension), dtype="float32")
        return np.asarray(
            service.index.reconstruct_n(0, service.index.ntotal),
            dtype="float32",
        )

    def test_legacy_snapshot_loads_for_retrieval_but_mutation_full_embeds(self):
        """旧快照缺 metadata 时仍可查询，但 mutation 必须全量生成新 metadata。"""
        service, model = self.create_snapshot({"A.txt": "AAAAAA"})
        os.remove(service.metadata_file_path)
        loaded = self.make_service(model)
        loaded.load_vector_store()
        self.assertEqual(loaded.index.ntotal, 2)
        self.assertIsNone(loaded.vector_metadata)

        self.write(loaded, "B.txt", "BBB")
        loaded.rebuild_index()

        self.assertEqual(model.encoded_texts, ["AAA", "AAA", "BBB"])
        self.assertTrue(Path(loaded.metadata_file_path).exists())

    def test_legacy_second_mutation_reuses_first_mutation_snapshot(self):
        """legacy 首次 mutation 建立 metadata 后，下一次应只编码新增文件。"""
        service, model = self.create_snapshot({"A.txt": "AAA"})
        os.remove(service.metadata_file_path)
        self.write(service, "B.txt", "BBB")
        service.rebuild_index()
        self.assertEqual(model.encoded_texts, ["AAA", "BBB"])
        model.clear()

        self.write(service, "C.txt", "CCC")
        service.rebuild_index()

        self.assertEqual(model.encoded_texts, ["CCC"])

    def test_unchanged_rebuild_does_not_encode(self):
        """完整 metadata 与内容均未变化时不得重复调用 Embedding。"""
        service, model = self.create_snapshot({"A.txt": "AAAAAA", "B.txt": "BBB"})
        service.rebuild_index()
        self.assertEqual(model.encoded_texts, [])

    def test_add_only_encodes_new_source(self):
        """新增 D 时 A/B/C 复用旧向量，encode 输入严格只有 D chunks。"""
        service, model = self.create_snapshot({
            "A.txt": "AAAAAA", "B.txt": "BBBBBB", "C.txt": "CCCCCC",
        })
        self.write(service, "D.txt", "DDDDDD")
        service.rebuild_index()
        self.assertEqual(model.encoded_texts, ["DDD", "DDD"])

    def test_add_earlier_filename_reorders_vectors_with_chunks(self):
        """新增排序靠前的文件后，复用向量仍必须跟随 Chunk 一起重排。"""
        service, model = self.create_snapshot({"A.txt": "AAA", "B.txt": "BBB"})
        self.write(service, "0.txt", "000")
        service.rebuild_index()
        expected = RecordingEmbeddingModel().encode(
            [chunk["text"] for chunk in service.chunks]
        )
        np.testing.assert_array_equal(self.vectors(service), expected)
        self.assertEqual(model.encoded_texts, ["000"])

    def test_modify_only_encodes_changed_source(self):
        """修改 B 时 A/C vectors 保持，只有新 B chunks 进入 encode。"""
        service, model = self.create_snapshot({
            "A.txt": "AAA", "B.txt": "BBB", "C.txt": "CCC",
        })
        before = self.vectors(service).copy()
        self.write(service, "B.txt", "B22")
        service.rebuild_index()
        after = self.vectors(service)
        self.assertEqual(model.encoded_texts, ["B22"])
        np.testing.assert_array_equal(after[[0, 2]], before[[0, 2]])

    def test_delete_does_not_encode_and_preserves_remaining_vectors(self):
        """删除 B 只丢弃其分组，A/C 不重新 Embedding。"""
        service, model = self.create_snapshot({
            "A.txt": "AAA", "B.txt": "BBB", "C.txt": "CCC",
        })
        before = self.vectors(service).copy()
        Path(service.content_path, "B.txt").unlink()
        service.rebuild_index()
        self.assertEqual(model.encoded_texts, [])
        np.testing.assert_array_equal(self.vectors(service), before[[0, 2]])

    def test_same_size_different_bytes_are_reembedded(self):
        """内容大小不变也必须由 SHA-256 检出变化。"""
        service, model = self.create_snapshot({"A.txt": "ABC"})
        self.write(service, "A.txt", "XYZ")
        service.rebuild_index()
        self.assertEqual(model.encoded_texts, ["XYZ"])

    def test_model_name_change_forces_full_embedding(self):
        """模型名变化时禁止混用两个向量空间。"""
        service, model = self.create_snapshot({"A.txt": "AAA", "B.txt": "BBB"})
        service.embedding_model_name = "fake-v2"
        service.rebuild_index()
        self.assertEqual(model.encoded_texts, ["AAA", "BBB"])

    def test_dimension_mismatch_forces_full_embedding(self):
        """metadata dimension 与当前模型不同时必须全量重建。"""
        service, model = self.create_snapshot({"A.txt": "AAA"})
        metadata = json.loads(Path(service.metadata_file_path).read_text(encoding="utf-8"))
        metadata["dimension"] = 99
        Path(service.metadata_file_path).write_text(json.dumps(metadata), encoding="utf-8")
        service.rebuild_index()
        self.assertEqual(model.encoded_texts, ["AAA"])

    def test_normalization_change_forces_full_embedding(self):
        """normalization policy 不一致时不能复用旧 vectors。"""
        service, model = self.create_snapshot({"A.txt": "AAA"})
        metadata = json.loads(Path(service.metadata_file_path).read_text(encoding="utf-8"))
        metadata["normalize_embeddings"] = True
        Path(service.metadata_file_path).write_text(json.dumps(metadata), encoding="utf-8")
        service.rebuild_index()
        self.assertEqual(model.encoded_texts, ["AAA"])

    def test_chunk_size_change_forces_full_embedding(self):
        """service 级 chunk_size 变化时整个 KB 必须重新切分和 Embedding。"""
        service, model = self.create_snapshot({"A.txt": "AAAA", "B.txt": "BBBB"})
        service.chunk_size = 2
        service.rebuild_index()
        self.assertEqual(model.encoded_texts, ["AA", "AA", "BB", "BB"])

    def test_chunk_overlap_change_forces_full_embedding(self):
        """service 级 overlap 变化时整个 KB 必须重新切分和 Embedding。"""
        service, model = self.create_snapshot(
            {"A.txt": "AAAA", "B.txt": "BBBB"}, chunk_size=3, overlap=0
        )
        service.chunk_overlap = 1
        service.rebuild_index()
        self.assertEqual(model.encoded_texts, ["AAA", "AA", "BBB", "BB"])

    def test_malformed_metadata_forces_full_embedding(self):
        """无法解析 metadata 时应保守 full rebuild，而不是猜测兼容。"""
        service, model = self.create_snapshot({"A.txt": "AAA"})
        Path(service.metadata_file_path).write_text("{bad", encoding="utf-8")
        service.rebuild_index()
        self.assertEqual(model.encoded_texts, ["AAA"])

    def test_unsupported_metadata_version_forces_full_embedding(self):
        """未知 format_version 必须禁用旧向量复用。"""
        service, model = self.create_snapshot({"A.txt": "AAA"})
        metadata = json.loads(Path(service.metadata_file_path).read_text(encoding="utf-8"))
        metadata["format_version"] = 999
        Path(service.metadata_file_path).write_text(json.dumps(metadata), encoding="utf-8")
        service.rebuild_index()
        self.assertEqual(model.encoded_texts, ["AAA"])

    def test_source_metadata_mismatch_forces_full_embedding(self):
        """source chunk_count 与 chunks.json 不一致时必须放弃复用。"""
        service, model = self.create_snapshot({"A.txt": "AAAAAA"})
        metadata = json.loads(Path(service.metadata_file_path).read_text(encoding="utf-8"))
        metadata["sources"]["A.txt"]["chunk_count"] = 1
        Path(service.metadata_file_path).write_text(json.dumps(metadata), encoding="utf-8")
        service.rebuild_index()
        self.assertEqual(model.encoded_texts, ["AAA", "AAA"])

    def test_metadata_invalid_types_and_hash_force_full_embedding(self):
        """bool 冒充 int、空模型名或非法 SHA-256 都必须让整个 KB full rebuild。"""
        invalid_cases = (
            ("format_version_bool", lambda data: data.__setitem__("format_version", True)),
            ("pipeline_version_bool", lambda data: data.__setitem__("embedding_pipeline_version", True)),
            ("normalization_int", lambda data: data.__setitem__("normalize_embeddings", 0)),
            ("overlap_bool", lambda data: data.__setitem__("chunk_overlap", False)),
            ("empty_model", lambda data: data.__setitem__("embedding_model", "")),
            ("dimension_string", lambda data: data.__setitem__("dimension", "3")),
            (
                "chunk_count_bool",
                lambda data: data["sources"]["A.txt"].__setitem__("chunk_count", True),
            ),
            (
                "invalid_sha256",
                lambda data: data["sources"]["A.txt"].__setitem__("sha256", "not-a-hash"),
            ),
        )

        for name, mutate in invalid_cases:
            with self.subTest(name=name):
                service, model = self.create_snapshot({"A.txt": "AAA", "B.txt": "BBB"})
                metadata = json.loads(
                    Path(service.metadata_file_path).read_text(encoding="utf-8")
                )
                mutate(metadata)
                Path(service.metadata_file_path).write_text(
                    json.dumps(metadata),
                    encoding="utf-8",
                )

                service.rebuild_index()

                self.assertEqual(model.encoded_texts, ["AAA", "BBB"])

    def test_same_count_cross_generation_snapshot_forces_full_embedding(self):
        """Chunk 数相同但 chunks/index generation 不同时不得复用旧 vectors。"""
        service, model = self.create_snapshot({"A.txt": "AAA"})
        Path(service.chunks_file_path).write_text(
            json.dumps([{"text": "BBB", "source": "A.txt", "chunk_id": 1}]),
            encoding="utf-8",
        )
        self.write(service, "A.txt", "BBB")

        loaded = self.make_service(model)
        with self.assertRaises(ValueError):
            loaded.load_vector_store()

        service.rebuild_index()
        self.assertEqual(model.encoded_texts, ["BBB"])

    def test_reconstructed_vectors_keep_dtype_order_and_dimension(self):
        """复用路径恢复的 vectors 必须保持 float32、顺序和维度。"""
        service, _ = self.create_snapshot({"A.txt": "AAA", "B.txt": "BBB"})
        expected = self.vectors(service).copy()
        service.rebuild_index()
        actual = self.vectors(service)
        self.assertEqual(actual.dtype, np.float32)
        self.assertEqual(actual.shape, (2, 3))
        np.testing.assert_array_equal(actual, expected)

    def test_incremental_and_full_indexes_return_same_vector_results(self):
        """相同最终 content 的 incremental 与 full FAISS 搜索结果必须一致。"""
        incremental, _ = self.create_snapshot({"A.txt": "AAA", "C.txt": "CCC"})
        self.write(incremental, "B.txt", "BBB")
        incremental.rebuild_index()

        full_model = RecordingEmbeddingModel()
        full = self.make_service(full_model)
        for filename, text in {"A.txt": "AAA", "B.txt": "BBB", "C.txt": "CCC"}.items():
            self.write(full, filename, text)
        full.build_index()
        query = full_model.encode(["BBB"])
        inc_dist, inc_pos = incremental.index.search(query, 3)
        full_dist, full_pos = full.index.search(query, 3)
        np.testing.assert_array_equal(inc_pos, full_pos)
        np.testing.assert_array_equal(inc_dist, full_dist)

    def test_chunk_ids_and_faiss_positions_remain_aligned(self):
        """mutation 后仍保持 chunk_id=position+1 和一向量对应一 Chunk。"""
        service, _ = self.create_snapshot({"B.txt": "BBBBBB"})
        self.write(service, "A.txt", "AAA")
        service.rebuild_index()
        self.assertEqual(
            [chunk["chunk_id"] for chunk in service.chunks],
            list(range(1, len(service.chunks) + 1)),
        )
        self.assertEqual(service.index.ntotal, len(service.chunks))

    def test_bm25_rebuild_contains_all_final_chunks(self):
        """向量增量复用后 BM25 仍必须从最终完整 Chunk 集合刷新。"""
        service, _ = self.create_snapshot({"A.txt": "alpha", "B.txt": "beta"})
        self.write(service, "C.txt", "gamma")
        service.rebuild_index()
        self.assertEqual(len(service._bm25_docs), len(service.chunks))
        self.assertIn("gam", service._bm25_doc_freqs)
        self.assertIn("ma", service._bm25_doc_freqs)

    def test_db_sync_receives_final_global_chunk_mapping(self):
        """Phase D bulk sync 应继续接收重新编号后的完整文件映射。"""
        service, _ = self.create_snapshot({"B.txt": "BBBBBB"})
        self.write(service, "A.txt", "AAA")
        service.rebuild_index()
        with patch.object(kb_module, "sync_kb_file_mappings") as sync:
            service._sync_current_mappings()
        files = sync.call_args.args[1]
        self.assertEqual([item["filename"] for item in files], ["A.txt", "B.txt"])
        self.assertEqual(files[0]["chunk_ids"], [1])
        self.assertEqual(files[1]["chunk_ids"], [2, 3])

    def test_same_kb_services_share_phase_d_lock(self):
        """Phase E rebuild 继续使用 Phase D 的 per-user+KB mutation lock。"""
        first = self.make_service()
        second = self.make_service()
        first.mutation_lock = kb_module.get_kb_mutation_lock(7, "shared")
        second.mutation_lock = kb_module.get_kb_mutation_lock(7, "shared")
        self.assertIs(first.mutation_lock, second.mutation_lock)

    def test_metadata_write_failure_keeps_old_file_and_cleans_staging(self):
        """metadata replace 失败时旧文件保留，且不遗留本次 staging。"""
        service, _ = self.create_snapshot({"A.txt": "AAA"})
        old = Path(service.metadata_file_path).read_bytes()
        real_replace = os.replace

        def fail_metadata(source, target):
            if target == service.metadata_file_path:
                raise OSError("metadata replace failed")
            return real_replace(source, target)

        with patch.object(kb_module.os, "replace", side_effect=fail_metadata):
            with self.assertRaisesRegex(OSError, "metadata replace failed"):
                service.save_vector_store()

        self.assertEqual(Path(service.metadata_file_path).read_bytes(), old)
        self.assertEqual(
            list(Path(service.vector_store_path).glob("metadata.json.staging-*")),
            [],
        )

    def test_metadata_replace_failure_cannot_reuse_changed_source_next_time(self):
        """chunks/index 已更新但 metadata 仍旧时，下次 mutation 必须重算变化 source。"""
        service, model = self.create_snapshot({"A.txt": "AAA"})
        self.write(service, "A.txt", "BBB")
        real_replace = os.replace

        def fail_metadata(source, target):
            if target == service.metadata_file_path:
                raise OSError("metadata replace failed")
            return real_replace(source, target)

        with patch.object(kb_module.os, "replace", side_effect=fail_metadata):
            with self.assertRaisesRegex(OSError, "metadata replace failed"):
                service.rebuild_index()

        model.clear()
        self.write(service, "C.txt", "CCC")
        service.rebuild_index()

        self.assertEqual(model.encoded_texts, ["BBB", "CCC"])

    def test_add_five_chunks_only_encodes_five_of_twenty(self):
        """15 个旧 Chunk 加 5 个新 Chunk 时，实际 encode 输入必须只有 5 个。"""
        service, model = self.create_snapshot(
            {"A.txt": "A" * 10, "B.txt": "B" * 10, "C.txt": "C" * 10},
            chunk_size=2,
        )
        self.write(service, "D.txt", "D" * 10)
        service.rebuild_index()
        self.assertEqual(len(service.chunks), 20)
        self.assertEqual(len(model.encoded_texts), 5)

    def test_zip_import_discards_archived_vector_store(self):
        """ZIP 中的 index/chunks/metadata 必须在本机 service 初始化前被删除。"""
        zip_path = self.root / "import.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("metadata.json", json.dumps({"kb_name": "imported", "files": []}))
            archive.writestr("content/A.txt", "AAA")
            archive.writestr("vector_store/index.faiss", "untrusted")
            archive.writestr("vector_store/chunks.json", "[]")
            archive.writestr("vector_store/metadata.json", "{}")

        target = self.root / "imported"
        observed = {}

        class FakeService:
            def __init__(self, kb_name, user_id=None):
                observed["files"] = sorted(
                    path.name for path in (target / "vector_store").iterdir()
                )
                self.chunks = []

            def rebuild_and_sync(self):
                observed["rebuilt"] = True

        with (
            patch.object(import_service, "_kb_path", return_value=str(target)),
            patch.object(import_service, "create_kb"),
            patch.object(import_service, "_restore_file_metadata"),
            patch.object(import_service, "migrate_legacy_demo_files"),
            patch.object(import_service, "MiniKBService", FakeService),
        ):
            result = import_service.import_kb(str(zip_path), user_id=1)

        self.assertEqual(result["kb_name"], "imported")
        self.assertEqual(observed["files"], [])
        self.assertTrue(observed["rebuilt"])

    def test_zip_vector_store_delete_failure_stops_before_service_init(self):
        """归档 vector_store 无法删除时 import 必须失败，不能初始化 KB service。"""
        zip_path = self.root / "delete-failure.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("metadata.json", json.dumps({"kb_name": "imported", "files": []}))
            archive.writestr("content/A.txt", "AAA")
            archive.writestr("vector_store/index.faiss", "untrusted")

        target = self.root / "imported"
        initialized = []
        real_rmtree = import_service.shutil.rmtree

        class ForbiddenService:
            def __init__(self, *args, **kwargs):
                initialized.append(True)

            def rebuild_and_sync(self):
                return None

        def fail_unless_ignored(path, *args, **kwargs):
            if Path(path) == target / "vector_store":
                if kwargs.get("ignore_errors", False):
                    return None
                raise OSError("cannot remove imported vector store")
            return real_rmtree(path, *args, **kwargs)

        with (
            patch.object(import_service, "_kb_path", return_value=str(target)),
            patch.object(import_service, "create_kb"),
            patch.object(import_service, "_restore_file_metadata"),
            patch.object(import_service, "migrate_legacy_demo_files"),
            patch.object(import_service, "MiniKBService", ForbiddenService),
            patch.object(
                import_service.shutil,
                "rmtree",
                side_effect=fail_unless_ignored,
            ),
        ):
            with self.assertRaisesRegex(OSError, "cannot remove"):
                import_service.import_kb(str(zip_path), user_id=1)

        self.assertEqual(initialized, [])


if __name__ == "__main__":
    unittest.main()
