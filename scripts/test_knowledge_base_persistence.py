"""验证 Knowledge Base persistence 拆分后的行为、事务和用户隔离。"""

import inspect
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import db  # noqa: E402


class KnowledgeBasePersistenceTest(unittest.TestCase):
    """在隔离 SQLite 中覆盖 KB、文件元数据和 chunk 映射。"""

    def setUp(self):
        """每个测试使用独立数据库，避免修改真实知识库数据。"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        self.old_demo_cache = db._DEMO_USER_ID_CACHE
        db.DB_PATH = str(Path(self.temp_dir.name) / "mini.db")
        db._DEMO_USER_ID_CACHE = None
        db.init_db()
        self.user_a = db.create_user(email="kb-a@example.com")["id"]
        self.user_b = db.create_user(email="kb-b@example.com")["id"]

    def tearDown(self):
        """恢复 facade 的动态数据库配置并清理隔离数据。"""
        db.DB_PATH = self.old_db_path
        db._DEMO_USER_ID_CACHE = self.old_demo_cache
        self.temp_dir.cleanup()

    def test_kb_crud_and_user_isolation(self):
        """同名 KB 必须按 user_id 隔离，删除一方不能影响另一方。"""
        db.create_kb("shared", user_id=self.user_a)
        db.create_kb("shared", user_id=self.user_b)

        self.assertEqual([item["kb_name"] for item in db.list_kbs(self.user_a)], ["shared"])
        self.assertEqual(db.get_kb_record("shared", self.user_a)["user_id"], self.user_a)
        self.assertTrue(db.user_owns_kb("shared", self.user_a))
        self.assertTrue(db.user_owns_kb("shared", self.user_b))

        db.delete_kb_record("shared", user_id=self.user_a)

        self.assertIsNone(db.get_kb_record("shared", self.user_a))
        self.assertIsNotNone(db.get_kb_record("shared", self.user_b))

    def test_file_crud_status_and_docs_count(self):
        """文件元数据的新增、状态更新、docs_count 和删除保持原语义。"""
        db.create_kb("files", user_id=self.user_a)
        db.upsert_file_record(
            "files",
            "report.txt",
            128,
            3,
            chunk_size=400,
            chunk_overlap=40,
            content_path="content/report.txt",
            upload_path="uploads/report.txt",
            user_id=self.user_a,
        )

        record = db.list_file_records("files", user_id=self.user_a)[0]
        self.assertEqual(record["docs_count"], 3)
        self.assertEqual(record["chunk_size"], 400)
        self.assertEqual(db.list_file_records("files", user_id=self.user_b), [])

        db.update_file_status(
            "files",
            "report.txt",
            "failed",
            "parse failed",
            user_id=self.user_a,
        )
        updated = db.list_file_records("files", user_id=self.user_a)[0]
        self.assertEqual(updated["status"], "failed")
        self.assertEqual(updated["error"], "parse failed")

        db.delete_file_record("files", "report.txt", user_id=self.user_b)
        self.assertEqual(len(db.list_file_records("files", user_id=self.user_a)), 1)
        db.delete_file_record("files", "report.txt", user_id=self.user_a)
        self.assertEqual(db.list_file_records("files", user_id=self.user_a), [])

    def test_file_doc_mapping_crud_is_user_scoped(self):
        """file_doc 的新增、排序读取和删除不能跨用户影响同名文件。"""
        for user_id in (self.user_a, self.user_b):
            db.create_kb("mapping", user_id=user_id)
            db.add_file_doc("mapping", "same.txt", 2, user_id=user_id)
            db.add_file_doc("mapping", "same.txt", 1, user_id=user_id)

        self.assertEqual(
            db.list_file_docs("mapping", "same.txt", user_id=self.user_a),
            [{"chunk_id": 1}, {"chunk_id": 2}],
        )
        db.delete_file_docs("mapping", "same.txt", user_id=self.user_a)
        self.assertEqual(db.list_file_docs("mapping", "same.txt", self.user_a), [])
        self.assertEqual(len(db.list_file_docs("mapping", "same.txt", self.user_b)), 2)

    def test_sync_updates_docs_count_and_preserves_file_metadata(self):
        """批量同步应更新 docs_count 和映射，同时保留未覆盖的文件配置。"""
        db.create_kb("sync", user_id=self.user_a)
        db.upsert_file_record(
            "sync",
            "a.txt",
            3,
            1,
            status="failed",
            error="old error",
            chunk_size=512,
            chunk_overlap=64,
            content_path="content/a.txt",
            upload_path="uploads/a.txt",
            user_id=self.user_a,
        )

        db.sync_kb_file_mappings(
            "sync",
            [{"filename": "a.txt", "size": 9, "chunk_ids": [4, 5, 6]}],
            user_id=self.user_a,
        )

        record = db.list_file_records("sync", user_id=self.user_a)[0]
        self.assertEqual(record["docs_count"], 3)
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["chunk_size"], 512)
        self.assertEqual(
            db.list_file_docs("sync", "a.txt", user_id=self.user_a),
            [{"chunk_id": 4}, {"chunk_id": 5}, {"chunk_id": 6}],
        )

    def test_sync_failure_rolls_back_and_closes_connection(self):
        """同步中途失败必须恢复旧映射，并关闭执行该事务的 connection。"""
        db.create_kb("atomic", user_id=self.user_a)
        db.sync_kb_file_mappings(
            "atomic",
            [{"filename": "a.txt", "size": 3, "chunk_ids": [1]}],
            user_id=self.user_a,
        )
        real_connection = db.get_connection
        tracked = []

        class FailingCursor:
            def __init__(self, cursor):
                self.cursor = cursor

            def execute(self, sql, params=()):
                if "INSERT INTO file_doc" in sql:
                    raise RuntimeError("injected mapping failure")
                return self.cursor.execute(sql, params)

            def __getattr__(self, name):
                return getattr(self.cursor, name)

        class FailingConnection:
            def __init__(self, connection):
                self.connection = connection
                self.rollback_calls = 0
                self.close_calls = 0

            def cursor(self):
                return FailingCursor(self.connection.cursor())

            def rollback(self):
                self.rollback_calls += 1
                return self.connection.rollback()

            def close(self):
                self.close_calls += 1
                return self.connection.close()

            def __getattr__(self, name):
                return getattr(self.connection, name)

        def failing_connection():
            connection = FailingConnection(real_connection())
            tracked.append(connection)
            return connection

        with patch.object(db, "get_connection", side_effect=failing_connection):
            with self.assertRaisesRegex(RuntimeError, "injected mapping failure"):
                db.sync_kb_file_mappings(
                    "atomic",
                    [{"filename": "a.txt", "size": 6, "chunk_ids": [7, 8]}],
                    user_id=self.user_a,
                )

        self.assertEqual(tracked[0].rollback_calls, 1)
        self.assertGreaterEqual(tracked[0].close_calls, 1)
        self.assertEqual(
            db.list_file_docs("atomic", "a.txt", user_id=self.user_a),
            [{"chunk_id": 1}],
        )

    def test_db_facade_keeps_public_kb_signatures(self):
        """现有调用方仍可从 backend.db 使用原函数名和参数顺序。"""
        expected = {
            "create_default_kb": "(user_id=None)",
            "list_kbs": "(user_id=None)",
            "get_kb_record": "(kb_name, user_id=None)",
            "user_owns_kb": "(kb_name, user_id=None)",
            "create_kb": "(kb_name, user_id=None)",
            "upsert_file_record": (
                "(kb_name, file_name, file_size, docs_count, status='indexed', "
                "error=None, chunk_size=300, chunk_overlap=50, content_path=None, "
                "upload_path=None, user_id=None)"
            ),
            "update_file_status": "(kb_name, file_name, status, error=None, user_id=None)",
            "delete_file_record": "(kb_name, file_name, user_id=None)",
            "list_file_records": "(kb_name, user_id=None)",
            "add_file_doc": "(kb_name, file_name, chunk_id, user_id=None)",
            "delete_file_docs": "(kb_name, file_name, user_id=None)",
            "list_file_docs": "(kb_name, file_name, user_id=None)",
            "sync_kb_file_mappings": "(kb_name, files, user_id=None)",
            "delete_file_docs_by_kb": "(kb_name, user_id=None)",
            "delete_files_by_kb": "(kb_name, user_id=None)",
            "delete_kb_record": "(kb_name, user_id=None)",
        }

        for name, signature in expected.items():
            self.assertEqual(str(inspect.signature(getattr(db, name))), signature)


if __name__ == "__main__":
    unittest.main()
