"""验证普通上传始终写入请求明确指定且属于当前用户的知识库。"""

import io
import json
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import numpy as np
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

TEST_RUNTIME = tempfile.TemporaryDirectory()
os.environ["MINI_CHATCHAT_DB_PATH"] = str(Path(TEST_RUNTIME.name) / "mini.db")
os.environ["MINI_CHATCHAT_DATA_ROOT"] = str(Path(TEST_RUNTIME.name) / "data")
os.environ["MINI_CHATCHAT_UPLOADS_DIR"] = str(Path(TEST_RUNTIME.name) / "uploads")


class FakeEmbeddingModel:
    """让上传回归覆盖真实 FAISS 写入，同时避免测试加载外部模型。"""

    def encode(self, texts):
        """为每个 chunk 返回稳定、非空的二维向量。"""
        return np.asarray(
            [[float(index + 1), float(len(text))] for index, text in enumerate(texts)],
            dtype="float32",
        )

    def get_sentence_embedding_dimension(self):
        """声明与测试向量一致的维度，供 snapshot metadata 校验。"""
        return 2


import services.kb_service as kb_service_module  # noqa: E402

kb_service_module.get_embedding_model = lambda _name: FakeEmbeddingModel()

import app as backend_app  # noqa: E402
from auth.dependencies import get_current_user_optional  # noqa: E402
from auth.models import AuthenticatedUser  # noqa: E402
from db import (  # noqa: E402
    create_kb,
    create_user,
    list_file_docs,
    list_file_records,
)
from fastapi.testclient import TestClient  # noqa: E402
from user_scope import get_user_kb_root  # noqa: E402


class KnowledgeBaseUploadTargetingTest(unittest.TestCase):
    """覆盖 default、非 default、PDF、竞态和非法目标 KB。"""

    @classmethod
    def setUpClass(cls):
        """创建隔离用户和两个可写知识库。"""
        user = create_user(
            email="kb-upload-target@example.test",
            display_name="KB Upload Target",
        )
        cls.user_id = int(user["id"] if isinstance(user, dict) else user)
        cls.current_user = AuthenticatedUser(
            id=cls.user_id,
            email="kb-upload-target@example.test",
            display_name="KB Upload Target",
            avatar_url=None,
            auth_provider="email",
            is_guest=False,
            is_active=True,
        )
        create_kb("default", user_id=cls.user_id)
        create_kb("个人简历", user_id=cls.user_id)
        other_user = create_user(
            email="kb-upload-other-owner@example.test",
            display_name="Other KB Owner",
        )
        cls.other_user_id = int(
            other_user["id"] if isinstance(other_user, dict) else other_user
        )
        create_kb("other-users-kb", user_id=cls.other_user_id)
        backend_app.app.dependency_overrides[get_current_user_optional] = (
            lambda: cls.current_user
        )
        cls.client = TestClient(backend_app.app, raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls):
        """恢复 FastAPI dependency，并关闭隔离 runtime。"""
        cls.client.close()
        backend_app.app.dependency_overrides.clear()
        TEST_RUNTIME.cleanup()

    def setUp(self):
        """每个用例使用唯一文件名，避免索引结果相互覆盖。"""
        self.root = Path(get_user_kb_root(self.user_id))

    def _upload(self, kb_name, filename, content, content_type="text/plain"):
        """通过真实 multipart route 上传到明确指定的知识库。"""
        return self.client.post(
            "/upload",
            data={"kb_name": kb_name},
            files={"file": (filename, content, content_type)},
        )

    def _assert_indexed_only_in(self, filename, target_kb, other_kb):
        """同时验证文件、snapshot 和 DB mapping 只属于目标 KB。"""
        stem_name = f"{Path(filename).stem}.txt"
        target = self.root / target_kb
        other = self.root / other_kb
        self.assertTrue((target / "uploads" / filename).is_file())
        self.assertTrue((target / "content" / stem_name).is_file())
        self.assertTrue((target / "vector_store" / "index.faiss").is_file())
        chunks = json.loads(
            (target / "vector_store" / "chunks.json").read_text(encoding="utf-8")
        )
        self.assertTrue(any(chunk["source"] == stem_name for chunk in chunks))
        metadata = json.loads(
            (target / "vector_store" / "metadata.json").read_text(encoding="utf-8")
        )
        self.assertIn(stem_name, metadata["sources"])
        records = list_file_records(target_kb, user_id=self.user_id)
        self.assertTrue(any(record["filename"] == stem_name for record in records))
        self.assertGreater(len(list_file_docs(target_kb, stem_name, user_id=self.user_id)), 0)
        self.assertFalse((other / "uploads" / filename).exists())
        self.assertFalse((other / "content" / stem_name).exists())
        other_records = list_file_records(other_kb, user_id=self.user_id)
        self.assertFalse(any(record["filename"] == stem_name for record in other_records))
        return chunks

    def test_default_txt_upload_targets_default(self):
        """显式 default 上传应继续写入 default。"""
        response = self._upload("default", "default-target.txt", b"default target")
        self.assertEqual(response.status_code, 200, response.text)
        self._assert_indexed_only_in("default-target.txt", "default", "个人简历")

    def test_non_default_txt_ignores_stale_current_kb(self):
        """即使 server current KB 是 default，请求指定的非 default KB 仍应获胜。"""
        backend_app.set_current_kb_name(self.current_user, "default")
        response = self._upload(
            "个人简历",
            "resume-target.txt",
            "实习项目：构建知识库检索系统。".encode("utf-8"),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self._assert_indexed_only_in("resume-target.txt", "个人简历", "default")

    def test_delayed_switch_cannot_redirect_explicit_upload(self):
        """延迟 /switch_kb 时，并发上传仍必须使用 multipart 指定的目标 KB。"""
        backend_app.set_current_kb_name(self.current_user, "default")
        switch_entered = threading.Event()
        release_switch = threading.Event()
        original_set_current = backend_app.set_current_kb_name

        def delayed_set_current(current_user, kb_name):
            switch_entered.set()
            release_switch.wait(timeout=5)
            return original_set_current(current_user, kb_name)

        with patch.object(
            backend_app,
            "set_current_kb_name",
            side_effect=delayed_set_current,
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                switch_future = executor.submit(
                    self.client.post,
                    "/switch_kb",
                    json={"kb_name": "个人简历"},
                )
                self.assertTrue(switch_entered.wait(timeout=2))
                upload_response = self._upload(
                    "个人简历",
                    "race-target.txt",
                    b"explicit target wins over delayed switch",
                )
                release_switch.set()
                switch_response = switch_future.result(timeout=5)

        self.assertEqual(upload_response.status_code, 200, upload_response.text)
        self.assertEqual(switch_response.status_code, 200, switch_response.text)
        self._assert_indexed_only_in(
            "race-target.txt",
            "个人简历",
            "default",
        )

    def test_non_default_pdf_is_parsed_and_indexed(self):
        """PDF 上传到非 default KB 后应产生正文、chunks 和索引。"""
        pdf = io.BytesIO()
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        font_ref = writer._add_object(font)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})
        })
        stream = DecodedStreamObject()
        stream.set_data(
            b"BT /F1 12 Tf 72 720 Td (Resume internship retrieval project) Tj ET"
        )
        page[NameObject("/Contents")] = writer._add_object(stream)
        writer.write(pdf)

        response = self._upload(
            "个人简历",
            "resume-target.pdf",
            pdf.getvalue(),
            "application/pdf",
        )
        self.assertEqual(response.status_code, 200, response.text)
        chunks = self._assert_indexed_only_in(
            "resume-target.pdf",
            "个人简历",
            "default",
        )
        self.assertTrue(
            any("internship retrieval project" in chunk["text"] for chunk in chunks)
        )

    def test_non_owned_kb_is_rejected_without_side_effects(self):
        """属于另一用户的 KB 应在 staging 和索引前返回 404。"""
        before = set(self.root.rglob("*"))
        other_root = Path(get_user_kb_root(self.other_user_id))
        other_before = set(other_root.rglob("*"))
        response = self._upload("other-users-kb", "blocked.txt", b"blocked")
        after = set(self.root.rglob("*"))
        other_after = set(other_root.rglob("*"))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(after, before)
        self.assertEqual(other_after, other_before)

    def test_invalid_kb_name_is_rejected_without_side_effects(self):
        """路径型 kb_name 应在任何文件系统副作用前被拒绝。"""
        before = set(self.root.rglob("*"))
        response = self._upload("../escape", "blocked-path.txt", b"blocked")
        after = set(self.root.rglob("*"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
