"""验证 Phase D 的 KB 映射、并发互斥与索引持久化正确性。"""

import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import faiss
import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import db  # noqa: E402
import rag  # noqa: E402
from services import kb_service as kb_module  # noqa: E402


class FakeEmbeddingModel:
    """提供稳定的小向量，使测试不依赖模型下载和推理环境。"""

    def encode(self, texts):
        """让每段文本得到可重复的二维 float32 向量。"""
        return np.asarray(
            [[float(len(text)), float(sum(map(ord, text)) % 997)] for text in texts],
            dtype="float32",
        )


class KBConsistencyTest(unittest.TestCase):
    """在临时 SQLite 和 KB 目录中验证一次完整 rebuild 的一致性边界。"""

    def setUp(self):
        """隔离数据库、content 和 vector_store，避免触碰真实用户数据。"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.old_db_path = db.DB_PATH
        self.old_demo_cache = db._DEMO_USER_ID_CACHE
        db.DB_PATH = str(self.root / "mini.db")
        db._DEMO_USER_ID_CACHE = None
        db.init_db()
        self.user_id = db.get_demo_user_id()
        db.create_kb("audit", user_id=self.user_id)
        self.model_patch = patch.object(
            kb_module,
            "get_embedding_model",
            return_value=FakeEmbeddingModel(),
        )
        self.migration_patch = patch.object(
            kb_module,
            "migrate_legacy_demo_files",
        )
        self.model_patch.start()
        self.migration_patch.start()

    def tearDown(self):
        """恢复模块级数据库配置，避免影响随后运行的旧回归。"""
        self.model_patch.stop()
        self.migration_patch.stop()
        db.DB_PATH = self.old_db_path
        db._DEMO_USER_ID_CACHE = self.old_demo_cache
        self.temp_dir.cleanup()

    def make_service(self, kb_name="audit", user_id=None):
        """创建只使用临时目录和 Fake Embedding 的正式 KB service。"""
        return kb_module.MiniKBService(
            kb_name,
            root_path=str(self.root / "kbs"),
            chunk_size=3,
            chunk_overlap=0,
            user_id=self.user_id if user_id is None else user_id,
        )

    def write_content(self, service, filename, text):
        """写入隔离 content 文件，作为 rebuild 的真实输入。"""
        Path(service.content_path, filename).write_text(text, encoding="utf-8")

    def current_mapping(self, service, filename):
        """从当前 chunks 计算某个文件应有的 chunk_id。"""
        return [
            chunk["chunk_id"]
            for chunk in service.chunks
            if chunk["source"] == filename
        ]

    def db_mapping(self, filename):
        """读取 file_doc 中当前文件实际保存的 chunk_id。"""
        return [
            row["chunk_id"]
            for row in db.list_file_docs("audit", filename, user_id=self.user_id)
        ]

    def test_content_files_are_chunked_in_deterministic_name_order(self):
        """相同文件集合不应受 os.listdir 返回顺序影响而改变 chunk_id。"""
        with tempfile.TemporaryDirectory() as content_dir:
            root = Path(content_dir)
            (root / "b.txt").write_text("bbb", encoding="utf-8")
            (root / "a.txt").write_text("aaa", encoding="utf-8")
            real_listdir = os.listdir
            with patch.object(rag.os, "listdir", side_effect=lambda p: list(reversed(real_listdir(p)))):
                chunks = rag.load_and_split_documents(root, chunk_size=3, overlap=0)
        self.assertEqual([chunk["source"] for chunk in chunks], ["a.txt", "b.txt"])

    def test_delete_rebuild_refreshes_all_remaining_file_doc_rows(self):
        """删除前置文件后，B/C 的数据库映射必须跟随全局 chunk_id 重新编号。"""
        service = self.make_service()
        for filename, text in (("A.txt", "A" * 9), ("B.txt", "B" * 9), ("C.txt", "C" * 6)):
            self.write_content(service, filename, text)
        service.rebuild_and_sync()

        service.delete_document("A.txt")

        self.assertEqual(self.db_mapping("A.txt"), [])
        self.assertEqual(self.db_mapping("B.txt"), self.current_mapping(service, "B.txt"))
        self.assertEqual(self.db_mapping("C.txt"), self.current_mapping(service, "C.txt"))

    def test_rebuild_refreshes_mapping_when_earlier_file_chunk_count_changes(self):
        """reindex 改变前置文件 chunk 数后，后续文件映射也必须一起刷新。"""
        service = self.make_service()
        self.write_content(service, "A.txt", "A" * 9)
        self.write_content(service, "B.txt", "B" * 6)
        service.rebuild_and_sync()
        self.write_content(service, "A.txt", "A" * 3)

        service.rebuild_and_sync()

        self.assertEqual(self.db_mapping("B.txt"), self.current_mapping(service, "B.txt"))

    def test_new_sorted_file_refreshes_existing_mappings(self):
        """新增排序靠前的文件后，已有文件不能继续保留旧的全局 chunk_id。"""
        service = self.make_service()
        self.write_content(service, "B.txt", "B" * 6)
        service.rebuild_and_sync()
        self.write_content(service, "A.txt", "A" * 3)

        service.rebuild_and_sync()

        self.assertEqual(self.db_mapping("A.txt"), self.current_mapping(service, "A.txt"))
        self.assertEqual(self.db_mapping("B.txt"), self.current_mapping(service, "B.txt"))

    def test_reload_style_rebuild_repairs_stale_mapping(self):
        """显式 reload 使用的统一入口应重建全部 file_doc，而不只重写索引文件。"""
        service = self.make_service()
        self.write_content(service, "A.txt", "A" * 3)
        self.write_content(service, "B.txt", "B" * 3)
        service.rebuild_and_sync()
        db.delete_file_docs("audit", "B.txt", user_id=self.user_id)

        service.rebuild_and_sync()

        self.assertEqual(self.db_mapping("B.txt"), self.current_mapping(service, "B.txt"))

    def test_bulk_sync_rolls_back_all_file_doc_changes_on_insert_failure(self):
        """事务中途写入失败时，旧映射必须完整保留，不能只剩半套新记录。"""
        service = self.make_service()
        self.write_content(service, "A.txt", "A" * 3)
        service.rebuild_and_sync()
        before = self.db_mapping("A.txt")
        real_connection = db.get_connection

        class FailingCursor:
            def __init__(self, cursor):
                self.cursor = cursor

            def execute(self, sql, params=()):
                if "INSERT INTO file_doc" in sql:
                    raise RuntimeError("injected file_doc failure")
                return self.cursor.execute(sql, params)

            def __getattr__(self, name):
                return getattr(self.cursor, name)

        class FailingConnection:
            def __init__(self, connection):
                self.connection = connection

            def cursor(self):
                return FailingCursor(self.connection.cursor())

            def __getattr__(self, name):
                return getattr(self.connection, name)

        with patch.object(db, "get_connection", side_effect=lambda: FailingConnection(real_connection())):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                db.sync_kb_file_mappings(
                    "audit",
                    [{"filename": "A.txt", "size": 3, "chunk_ids": [9]}],
                    user_id=self.user_id,
                )

        self.assertEqual(self.db_mapping("A.txt"), before)

    def test_bulk_sync_isolated_for_different_users_with_same_kb_name(self):
        """同步 User A 的 shared KB 时，User B 同名 KB 的文件记录必须完全不变。"""
        other_user_id = db.create_user(
            email="phase-d-user-b@example.com",
            display_name="Phase D User B",
        )["id"]
        db.create_kb("shared", user_id=self.user_id)
        db.create_kb("shared", user_id=other_user_id)
        db.sync_kb_file_mappings(
            "shared",
            [{"filename": "same.txt", "size": 3, "chunk_ids": [1]}],
            user_id=self.user_id,
        )
        db.sync_kb_file_mappings(
            "shared",
            [{"filename": "same.txt", "size": 99, "chunk_ids": [9, 10]}],
            user_id=other_user_id,
        )
        user_b_files_before = db.list_file_records("shared", user_id=other_user_id)
        user_b_docs_before = db.list_file_docs(
            "shared",
            "same.txt",
            user_id=other_user_id,
        )

        db.sync_kb_file_mappings(
            "shared",
            [{"filename": "same.txt", "size": 6, "chunk_ids": [2, 3]}],
            user_id=self.user_id,
        )

        self.assertEqual(
            db.list_file_records("shared", user_id=other_user_id),
            user_b_files_before,
        )
        self.assertEqual(
            db.list_file_docs("shared", "same.txt", user_id=other_user_id),
            user_b_docs_before,
        )

    def test_same_user_and_kb_share_lock_but_other_scopes_do_not(self):
        """锁只串行化同一用户同一 KB，不应把所有知识库放进一个全局大锁。"""
        first = self.make_service()
        second = self.make_service()
        other_kb = self.make_service(kb_name="other")
        other_user = self.make_service(user_id=self.user_id + 1000)
        self.assertIs(first.mutation_lock, second.mutation_lock)
        self.assertIsNot(first.mutation_lock, other_kb.mutation_lock)
        self.assertIsNot(first.mutation_lock, other_user.mutation_lock)

    def test_same_kb_mutation_lock_serializes_two_services(self):
        """两个 service 对同一 KB 的 critical section 不得交错执行。"""
        first = self.make_service()
        second = self.make_service()
        entered = threading.Event()
        release = threading.Event()
        second_entered = threading.Event()

        def hold_first():
            with first.mutation_lock:
                entered.set()
                release.wait(2)

        def enter_second():
            entered.wait(2)
            with second.mutation_lock:
                second_entered.set()

        one = threading.Thread(target=hold_first)
        two = threading.Thread(target=enter_second)
        one.start(); two.start()
        self.assertTrue(entered.wait(1))
        self.assertFalse(second_entered.wait(0.1))
        release.set(); one.join(2); two.join(2)
        self.assertTrue(second_entered.is_set())

    def test_concurrent_same_kb_mutations_finish_with_one_consistent_snapshot(self):
        """并发新增文件最终必须留下数量匹配的索引、chunks 和完整 DB 映射。"""
        first = self.make_service()
        second = self.make_service()
        errors = []

        def add_file(service, filename, text):
            try:
                with service.mutation_lock:
                    self.write_content(service, filename, text)
                    service.rebuild_and_sync()
            except Exception as exc:
                errors.append(exc)

        one = threading.Thread(target=add_file, args=(first, "A.txt", "A" * 6))
        two = threading.Thread(target=add_file, args=(second, "B.txt", "B" * 6))
        one.start(); two.start(); one.join(3); two.join(3)

        loaded = self.make_service()
        self.assertEqual(errors, [])
        self.assertEqual(loaded.index.ntotal, len(loaded.chunks))
        for filename in ("A.txt", "B.txt"):
            self.assertEqual(self.db_mapping(filename), self.current_mapping(loaded, filename))

    def test_atomic_chunks_failure_preserves_old_destination_and_cleans_staging(self):
        """JSON staging 写失败时，旧 chunks.json 必须保持原样且不遗留临时文件。"""
        service = self.make_service()
        old = Path(service.chunks_file_path).read_bytes()
        service.chunks = [{"text": "new", "source": "A.txt", "chunk_id": 1}]
        with patch.object(kb_module.json, "dump", side_effect=RuntimeError("json failure")):
            with self.assertRaisesRegex(RuntimeError, "json failure"):
                service.save_vector_store()
        self.assertEqual(Path(service.chunks_file_path).read_bytes(), old)
        self.assertEqual(list(Path(service.vector_store_path).glob("*.staging-*")), [])

    def test_atomic_faiss_failure_preserves_old_destination_and_cleans_staging(self):
        """FAISS staging 写失败时，旧 index.faiss 必须保持原样且不遗留临时文件。"""
        service = self.make_service()
        self.write_content(service, "A.txt", "abc")
        service.rebuild_index()
        old = Path(service.index_file_path).read_bytes()
        with patch.object(kb_module.faiss, "write_index", side_effect=RuntimeError("faiss failure")):
            with self.assertRaisesRegex(RuntimeError, "faiss failure"):
                service.save_vector_store()
        self.assertEqual(Path(service.index_file_path).read_bytes(), old)
        self.assertEqual(list(Path(service.vector_store_path).glob("*.staging-*")), [])

    def test_mismatched_snapshot_is_rebuilt_from_content(self):
        """FAISS 数量与 chunks 数量不同时，初始化必须拒绝旧快照并从 content 恢复。"""
        service = self.make_service()
        self.write_content(service, "A.txt", "abc")
        service.rebuild_index()
        Path(service.chunks_file_path).write_text("[]", encoding="utf-8")

        recovered = self.make_service()

        self.assertEqual(recovered.index.ntotal, 1)
        self.assertEqual(len(recovered.chunks), 1)

    def test_malformed_chunks_and_broken_faiss_are_rebuilt(self):
        """任一快照文件损坏都不能继续加载，应回到当前 content 重建。"""
        for broken in ("chunks", "index"):
            with self.subTest(broken=broken):
                service = self.make_service()
                self.write_content(service, "A.txt", "abc")
                service.rebuild_index()
                service.save_vector_store()
                if broken == "chunks":
                    Path(service.chunks_file_path).write_text("{bad", encoding="utf-8")
                else:
                    Path(service.index_file_path).write_bytes(b"broken")
                recovered = self.make_service()
                self.assertEqual(recovered.index.ntotal, len(recovered.chunks))

    def test_only_one_snapshot_file_and_empty_kb_recover_safely(self):
        """缺少配对文件时应重建；空 KB 则继续保持 index=None、chunks=[]。"""
        service = self.make_service()
        Path(service.index_file_path).write_bytes(b"orphan")
        Path(service.chunks_file_path).unlink(missing_ok=True)
        recovered = self.make_service()
        self.assertIsNone(recovered.index)
        self.assertEqual(recovered.chunks, [])

    def test_valid_snapshot_loads_and_basic_retrieval_still_works(self):
        """合法快照应直接加载，FAISS position 与 chunks 位置仍保持一致。"""
        service = self.make_service()
        self.write_content(service, "A.txt", "abc")
        service.rebuild_index()
        service.save_vector_store()
        loaded = self.make_service()
        self.assertEqual(loaded.index.ntotal, len(loaded.chunks))
        self.assertEqual(loaded.chunks[0]["source"], "A.txt")


if __name__ == "__main__":
    unittest.main()
