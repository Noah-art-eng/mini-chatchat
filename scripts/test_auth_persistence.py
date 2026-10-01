"""验证 Auth persistence 拆分后的行为、隔离和 db facade 兼容性。"""

import inspect
import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import db  # noqa: E402


class AuthPersistenceTest(unittest.TestCase):
    """在隔离 SQLite 中覆盖用户、OAuth、Session 和 Preferences。"""

    def setUp(self):
        """每个测试使用独立数据库，避免修改真实账号和认证会话。"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        self.old_demo_cache = db._DEMO_USER_ID_CACHE
        db.DB_PATH = str(Path(self.temp_dir.name) / "mini.db")
        db._DEMO_USER_ID_CACHE = None
        db.init_db()

    def tearDown(self):
        """恢复 facade 的动态数据库配置，避免影响后续回归。"""
        db.DB_PATH = self.old_db_path
        db._DEMO_USER_ID_CACHE = self.old_demo_cache
        self.temp_dir.cleanup()

    def create_email_user(self, suffix):
        """创建具有稳定密码摘要的测试用户。"""
        return db.create_email_user(
            f"{suffix}@example.com",
            f"hash-{suffix}",
            f"User {suffix}",
        )

    def test_user_create_lookup_and_update(self):
        """用户创建、邮箱查询、密码查询、状态和资料更新应保持原行为。"""
        user = self.create_email_user("alpha")

        self.assertEqual(db.get_user_by_id(user["id"])["email"], "alpha@example.com")
        self.assertEqual(db.get_user_by_email("alpha@example.com")["id"], user["id"])
        auth_user = db.get_user_auth_by_email("ALPHA@EXAMPLE.COM")
        self.assertEqual(auth_user["password_hash"], "hash-alpha")
        self.assertEqual(db.get_user_password_hash(user["id"]), "hash-alpha")
        self.assertNotIn("password_hash", db.public_user_dict(auth_user))

        updated = db.update_user_account(user["id"], "Renamed Alpha")
        self.assertEqual(updated["display_name"], "Renamed Alpha")
        self.assertTrue(db.set_user_active(user["id"], False))
        self.assertFalse(db.get_user_by_id(user["id"])["is_active"])
        self.assertTrue(db.set_user_active(user["id"], True))

    def test_oauth_accounts_are_scoped_to_their_user(self):
        """OAuth 身份只能由所属用户查询和删除，不能跨用户操作。"""
        user_a = self.create_email_user("oauth-a")
        user_b = self.create_email_user("oauth-b")
        account = db.upsert_oauth_account(
            user_a["id"],
            "github",
            "github-100",
            provider_email="oauth-a@example.com",
            provider_display_name="OAuth A",
        )

        self.assertEqual(account["user_id"], user_a["id"])
        self.assertEqual(
            db.get_oauth_account("github", "github-100")["user_id"],
            user_a["id"],
        )
        self.assertEqual(
            db.get_oauth_account_for_user(user_a["id"], "github")["id"],
            account["id"],
        )
        self.assertIsNone(
            db.get_oauth_account_for_user(user_b["id"], "github")
        )
        self.assertEqual(len(db.list_oauth_accounts_for_user(user_a["id"])), 1)
        self.assertEqual(db.list_oauth_accounts_for_user(user_b["id"]), [])
        self.assertEqual(db.user_login_method_count(user_a["id"]), 2)
        self.assertFalse(db.delete_oauth_account_for_user(user_b["id"], "github"))
        self.assertIsNotNone(db.get_oauth_account("github", "github-100"))
        self.assertTrue(db.delete_oauth_account_for_user(user_a["id"], "github"))

    def test_auth_sessions_support_rotation_revocation_expiry_and_isolation(self):
        """Session 轮换、撤销、过期清理和 user_id 限制应保持一致。"""
        user_a = self.create_email_user("session-a")
        user_b = self.create_email_user("session-b")
        active = db.create_auth_session(
            "session-active",
            user_a["id"],
            "refresh-a",
            "2999-01-01 00:00:00",
            user_agent="test",
            ip_address="127.0.0.1",
        )
        expired = db.create_auth_session(
            "session-expired",
            user_a["id"],
            "refresh-old",
            "2000-01-01 00:00:00",
        )
        db.create_auth_session(
            "session-b",
            user_b["id"],
            "refresh-b",
            "2999-01-01 00:00:00",
        )

        self.assertEqual(active["user_id"], user_a["id"])
        self.assertEqual(expired["session_id"], "session-expired")
        self.assertEqual(
            {item["session_id"] for item in db.list_auth_sessions_by_user(user_a["id"])},
            {"session-active", "session-expired"},
        )
        self.assertEqual(
            [item["session_id"] for item in db.list_auth_sessions_by_user(user_b["id"])],
            ["session-b"],
        )
        self.assertFalse(
            db.revoke_auth_session_for_user(user_b["id"], "session-active")
        )
        self.assertTrue(
            db.update_auth_session_refresh(
                "session-active",
                "refresh-rotated",
                "2999-02-01 00:00:00",
            )
        )
        self.assertEqual(
            db.get_auth_session("session-active")["refresh_token_hash"],
            "refresh-rotated",
        )

        self.assertEqual(db.cleanup_expired_auth_sessions(), 1)
        self.assertFalse(db.get_auth_session("session-expired")["is_active"])
        self.assertTrue(db.revoke_auth_session("session-active"))
        self.assertFalse(db.get_auth_session("session-active")["is_active"])
        self.assertEqual(db.revoke_user_auth_sessions(user_b["id"]), 1)

    def test_preferences_are_isolated_per_user(self):
        """偏好更新只能影响目标 user_id，不能覆盖另一用户设置。"""
        user_a = self.create_email_user("prefs-a")
        user_b = self.create_email_user("prefs-b")

        updated = db.upsert_user_preferences(
            user_a["id"],
            language="zh-CN",
            developer_mode=True,
            onboarding_completed=True,
            theme="dark",
            preferred_model="model-a",
        )
        untouched = db.get_user_preferences(user_b["id"])

        self.assertEqual(updated["language"], "zh-CN")
        self.assertTrue(updated["developer_mode"])
        self.assertEqual(updated["theme"], "dark")
        self.assertIsNone(untouched["language"])
        self.assertFalse(untouched["developer_mode"])
        self.assertEqual(untouched["theme"], "light")

    def test_db_facade_keeps_public_auth_signatures(self):
        """Auth 调用方继续从 backend.db 获得原函数名和参数顺序。"""
        expected = {
            "get_user_by_id": "(user_id)",
            "get_user_by_email": "(email)",
            "get_user_auth_by_email": "(email)",
            "create_email_user": "(email, password_hash, display_name=None)",
            "set_user_active": "(user_id, is_active)",
            "update_user_account": "(user_id, display_name)",
            "get_oauth_account": "(provider, provider_user_id)",
            "get_oauth_account_for_user": "(user_id, provider)",
            "list_oauth_accounts_for_user": "(user_id)",
            "delete_oauth_account_for_user": "(user_id, provider)",
            "get_auth_session": "(session_id)",
            "list_auth_sessions_by_user": "(user_id)",
            "revoke_auth_session": "(session_id)",
            "get_user_preferences": "(user_id)",
        }

        for name, signature in expected.items():
            exported = getattr(db, name)
            self.assertTrue(callable(exported))
            self.assertEqual(str(inspect.signature(exported)), signature)


if __name__ == "__main__":
    unittest.main()
