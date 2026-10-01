"""验证 Conversation 持久化拆分后的行为与用户隔离保持不变。"""

import inspect
import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import db  # noqa: E402


class ConversationPersistenceTest(unittest.TestCase):
    """在隔离 SQLite 中覆盖会话、消息、反馈和 facade 兼容性。"""

    def setUp(self):
        """每个测试使用独立数据库，避免读写项目真实会话数据。"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        self.old_demo_cache = db._DEMO_USER_ID_CACHE
        db.DB_PATH = str(Path(self.temp_dir.name) / "mini.db")
        db._DEMO_USER_ID_CACHE = None
        db.init_db()
        self.user_a = db.create_user(
            email="conversation-a@example.com",
            display_name="Conversation A",
        )["id"]
        self.user_b = db.create_user(
            email="conversation-b@example.com",
            display_name="Conversation B",
        )["id"]

    def tearDown(self):
        """恢复 facade 的动态数据库配置，不影响后续测试。"""
        db.DB_PATH = self.old_db_path
        db._DEMO_USER_ID_CACHE = self.old_demo_cache
        self.temp_dir.cleanup()

    def test_conversation_message_feedback_lifecycle(self):
        """Conversation CRUD、消息 metadata 和 feedback 应保持原有返回结构。"""
        conversation_id = db.create_conversation("Original", user_id=self.user_a)

        self.assertEqual(
            [item["id"] for item in db.list_conversations(user_id=self.user_a)],
            [conversation_id],
        )
        self.assertEqual(
            db.get_conversation(conversation_id, user_id=self.user_a)["title"],
            "Original",
        )
        updated = db.update_conversation_title(
            conversation_id,
            "Renamed",
            user_id=self.user_a,
        )
        self.assertEqual(updated["title"], "Renamed")

        message_id = db.save_message(
            conversation_id,
            "assistant",
            "answer",
            metadata={"sources": [{"source": "guide.txt"}], "trace": "ok"},
            user_id=self.user_a,
        )
        messages = db.get_conversation_messages(
            conversation_id,
            user_id=self.user_a,
        )
        self.assertEqual([message["id"] for message in messages], [message_id])
        self.assertEqual(messages[0]["metadata"]["trace"], "ok")
        self.assertEqual(messages[0]["sources"], [{"source": "guide.txt"}])

        self.assertTrue(
            db.update_message_feedback(
                message_id,
                1,
                "useful",
                user_id=self.user_a,
            )
        )
        feedback = db.get_conversation_messages(
            conversation_id,
            user_id=self.user_a,
        )[0]
        self.assertEqual(feedback["feedback_score"], 1)
        self.assertEqual(feedback["feedback_reason"], "useful")

        self.assertTrue(db.delete_conversation(conversation_id, user_id=self.user_a))
        self.assertIsNone(db.get_conversation(conversation_id, user_id=self.user_a))
        self.assertEqual(
            db.get_conversation_messages(conversation_id, user_id=self.user_a),
            [],
        )

    def test_conversation_and_message_access_is_user_scoped(self):
        """另一用户不能读取、修改、写消息、反馈或删除不属于自己的会话。"""
        conversation_id = db.create_conversation("Private", user_id=self.user_a)
        message_id = db.save_message(
            conversation_id,
            "user",
            "secret",
            user_id=self.user_a,
        )

        self.assertEqual(db.list_conversations(user_id=self.user_b), [])
        self.assertIsNone(db.get_conversation(conversation_id, user_id=self.user_b))
        self.assertIsNone(
            db.update_conversation_title(
                conversation_id,
                "Hijacked",
                user_id=self.user_b,
            )
        )
        self.assertIsNone(
            db.save_message(
                conversation_id,
                "user",
                "injected",
                user_id=self.user_b,
            )
        )
        self.assertEqual(
            db.get_conversation_messages(conversation_id, user_id=self.user_b),
            [],
        )
        self.assertFalse(
            db.update_message_feedback(message_id, -1, user_id=self.user_b)
        )
        self.assertFalse(db.delete_conversation(conversation_id, user_id=self.user_b))

        owner_conversation = db.get_conversation(
            conversation_id,
            user_id=self.user_a,
        )
        owner_messages = db.get_conversation_messages(
            conversation_id,
            user_id=self.user_a,
        )
        self.assertEqual(owner_conversation["title"], "Private")
        self.assertEqual([message["content"] for message in owner_messages], ["secret"])
        self.assertIsNone(owner_messages[0]["feedback_score"])

    def test_db_facade_keeps_public_conversation_signatures(self):
        """现有调用方从 backend.db 导入时仍看到原函数名和参数顺序。"""
        expected = {
            "create_conversation": "(title=None, user_id=None)",
            "list_conversations": "(user_id=None)",
            "get_conversation": "(conversation_id, user_id=None)",
            "update_conversation_title": "(conversation_id, title, user_id=None)",
            "delete_conversation": "(conversation_id, user_id=None)",
            "save_message": "(conversation_id, role, content, metadata=None, user_id=None)",
            "get_conversation_messages": "(conversation_id, user_id=None)",
            "update_message_feedback": "(message_id, score, reason=None, user_id=None)",
        }

        for name, signature in expected.items():
            exported = getattr(db, name)
            self.assertTrue(callable(exported))
            self.assertEqual(str(inspect.signature(exported)), signature)

        self.assertEqual(db.decode_metadata(db.encode_metadata({"中文": "来源"})), {"中文": "来源"})


if __name__ == "__main__":
    unittest.main()
