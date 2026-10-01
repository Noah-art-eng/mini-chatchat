"""验证 SQLite 每连接 FK 配置以及 DB 方法的统一 rollback/close 保证。"""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import db  # noqa: E402
from user_scope import DEMO_USER_EMAIL  # noqa: E402


class TrackingConnection(sqlite3.Connection):
    """记录 rollback 与 close，验证异常路径不会只依赖对象回收。"""

    def __init__(self, *args, **kwargs):
        """初始化真实 SQLite connection，并建立调用计数。"""
        super().__init__(*args, **kwargs)
        self.rollback_calls = 0
        self.close_calls = 0
        self.fail_commit = False

    def commit(self):
        """允许测试注入 commit 失败，验证失败后的 rollback 与 close。"""
        if self.fail_commit:
            raise sqlite3.OperationalError("injected commit failure")
        return super().commit()

    def rollback(self):
        """记录显式 rollback 后继续执行 SQLite 原行为。"""
        self.rollback_calls += 1
        return super().rollback()

    def close(self):
        """记录显式 close 后继续执行 SQLite 原行为。"""
        self.close_calls += 1
        return super().close()


class DatabaseConnectionCorrectnessTest(unittest.TestCase):
    """覆盖 FK enforcement、成功关闭和异常 rollback/关闭。"""

    def setUp(self):
        """每个测试使用独立数据库，避免接触项目真实数据。"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "mini.db")
        self.original_connect = sqlite3.connect
        self.connections = []
        self.fail_commits = False

        def tracked_connect(*args, **kwargs):
            kwargs["factory"] = TrackingConnection
            connection = self.original_connect(*args, **kwargs)
            connection.fail_commit = self.fail_commits
            self.connections.append(connection)
            return connection

        self.db_path_patch = patch.object(db, "DB_PATH", self.db_path)
        self.connect_patch = patch.object(db.sqlite3, "connect", side_effect=tracked_connect)
        self.db_path_patch.start()
        self.connect_patch.start()
        db._DEMO_USER_ID_CACHE = None
        db.init_db()

    def tearDown(self):
        """恢复 DB 配置并清理隔离数据库。"""
        self.connect_patch.stop()
        self.db_path_patch.stop()
        db._DEMO_USER_ID_CACHE = None
        self.temp_dir.cleanup()

    def test_every_new_connection_enables_foreign_keys(self):
        """每次 get_connection 都必须启用 FK，并真实拒绝不存在的父记录。"""
        connection = db.get_connection()
        try:
            enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
            self.assertEqual(enabled, 1)
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO user_preferences (
                        user_id, developer_mode, onboarding_completed,
                        theme, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (999999, 0, 0, "light", "now", "now"),
                )
        finally:
            connection.close()

    def test_successful_db_method_closes_connection(self):
        """普通查询成功返回后，方法创建的 connection 必须已经关闭。"""
        db.get_user_by_id(-1)
        self.assertGreater(self.connections[-1].close_calls, 0)

    def test_exception_rolls_back_and_closes_connection(self):
        """SQL 异常必须 rollback 并立即 close，不能等待垃圾回收。"""
        with self.assertRaises(sqlite3.IntegrityError):
            db.create_user(
                email=DEMO_USER_EMAIL,
                display_name="duplicate",
                auth_provider="email",
            )

        failed_connection = self.connections[-1]
        self.assertGreater(failed_connection.rollback_calls, 0)
        self.assertGreater(failed_connection.close_calls, 0)

    def test_commit_failure_rolls_back_and_closes_connection(self):
        """commit 本身失败时也必须 rollback 并 close 当前 connection。"""
        self.fail_commits = True

        with self.assertRaises(sqlite3.OperationalError):
            db.set_user_active(999999, False)

        failed_connection = self.connections[-1]
        self.assertGreater(failed_connection.rollback_calls, 0)
        self.assertGreater(failed_connection.close_calls, 0)

    def test_init_db_is_repeatable_and_schema_is_ready(self):
        """拆分后的 schema 初始化应可重复执行，并保留关键表、迁移列和唯一约束。"""
        db.init_db()
        db.init_db()

        connection = db.get_connection()
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            self.assertTrue({"users", "knowledge_base", "knowledge_file", "message"} <= tables)

            message_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(message)").fetchall()
            }
            self.assertTrue({"feedback_score", "feedback_reason", "metadata", "user_id"} <= message_columns)

            cursor = connection.cursor()
            self.assertTrue(
                db.has_unique_index(cursor, "knowledge_base", ["user_id", "kb_name"])
            )
            self.assertTrue(
                db.has_unique_index(
                    cursor,
                    "knowledge_file",
                    ["user_id", "kb_name", "file_name"],
                )
            )
        finally:
            connection.close()

    def test_db_facade_keeps_connection_and_schema_exports(self):
        """原有调用方仍可从 backend.db 导入连接、初始化和迁移 helper。"""
        from db import (  # noqa: PLC0415
            connection_scope,
            ensure_user_scoped_unique_constraints,
            get_connection,
            has_unique_index,
            init_db,
        )

        for exported in (
            connection_scope,
            ensure_user_scoped_unique_constraints,
            get_connection,
            has_unique_index,
            init_db,
        ):
            self.assertTrue(callable(exported))

    def test_init_db_migrates_legacy_kb_tables_without_losing_rows(self):
        """旧版无 user_id 的 KB 表经 facade 初始化后应保留数据并补齐用户隔离约束。"""
        legacy_path = str(Path(self.temp_dir.name) / "legacy.db")
        connection = self.original_connect(legacy_path)
        try:
            connection.execute(
                """
                CREATE TABLE knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kb_name TEXT UNIQUE NOT NULL,
                    embed_model TEXT NOT NULL,
                    create_time TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE knowledge_file (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kb_name TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    docs_count INTEGER NOT NULL,
                    update_time TEXT NOT NULL,
                    UNIQUE(kb_name, file_name)
                )
                """
            )
            connection.execute(
                "INSERT INTO knowledge_base (kb_name, embed_model, create_time) "
                "VALUES ('legacy', 'model', 'now')"
            )
            connection.execute(
                "INSERT INTO knowledge_file "
                "(kb_name, file_name, file_size, docs_count, update_time) "
                "VALUES ('legacy', 'old.txt', 3, 1, 'now')"
            )
            connection.commit()
        finally:
            connection.close()

        current_path = db.DB_PATH
        try:
            db.DB_PATH = legacy_path
            db._DEMO_USER_ID_CACHE = None
            db.init_db()

            migrated = db.get_connection()
            try:
                kb_row = migrated.execute(
                    "SELECT kb_name, user_id FROM knowledge_base WHERE kb_name = 'legacy'"
                ).fetchone()
                file_row = migrated.execute(
                    "SELECT file_name, user_id FROM knowledge_file "
                    "WHERE kb_name = 'legacy'"
                ).fetchone()
                self.assertEqual(kb_row[0], "legacy")
                self.assertEqual(file_row[0], "old.txt")
                self.assertIsInstance(kb_row[1], int)
                self.assertEqual(file_row[1], kb_row[1])
                cursor = migrated.cursor()
                self.assertTrue(
                    db.has_unique_index(
                        cursor,
                        "knowledge_base",
                        ["user_id", "kb_name"],
                    )
                )
            finally:
                migrated.close()
        finally:
            db.DB_PATH = current_path
            db._DEMO_USER_ID_CACHE = None


if __name__ == "__main__":
    unittest.main()
