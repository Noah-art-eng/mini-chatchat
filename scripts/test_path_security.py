"""回归验证 Mini ChatChat 上传文件和创建知识库时的 Path Traversal 防护。

测试覆盖 ``backend/path_security.py`` 的名称校验与最终路径检查，也确认
``backend/app.py`` 中的上传、临时上传和创建知识库接口确实在业务处理前接入了
这些检查。危险输入必须被拒绝，合法英文、中文名称也不能被安全修复误伤。
"""

import asyncio
import io
import os
import sys
import tempfile
import unittest
import atexit
from pathlib import Path

import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

TEST_RUNTIME = tempfile.TemporaryDirectory()
atexit.register(TEST_RUNTIME.cleanup)
# 数据库、知识库和上传文件全部指向临时 runtime（本次测试的独立运行目录）。
# 这样 API 测试可以真实执行创建目录等操作，又不会修改项目现有 data、uploads
# 和 backend/mini.db 中的用户数据。
os.environ["MINI_CHATCHAT_DB_PATH"] = str(Path(TEST_RUNTIME.name) / "mini.db")
os.environ["MINI_CHATCHAT_DATA_ROOT"] = str(Path(TEST_RUNTIME.name) / "data")
os.environ["MINI_CHATCHAT_UPLOADS_DIR"] = str(Path(TEST_RUNTIME.name) / "uploads")

from path_security import (  # noqa: E402
    PathValidationError,
    is_safe_filename,
    is_safe_kb_name,
    safe_join,
)


class FakeEmbeddingModel:
    """替代项目把文本转成向量供 FAISS 检索使用的真实 Embedding 模型。"""

    def encode(self, texts):
        """返回足够让知识库索引初始化的最小向量；本测试不验证向量质量。"""
        return np.ones((len(texts), 2), dtype="float32")


import services.kb_service as kb_service_module  # noqa: E402

# backend/app.py 导入时会初始化知识库处理服务；该服务位于
# backend/services/kb_service.py，负责知识库文件、FAISS/BM25 索引和检索，并会
# 取得 Embedding 模型。本测试只验证路径安全，因此必须在导入 app.py 前换成 Fake，
# 避免模型下载、网络或推理环境决定测试是否通过。
kb_service_module.get_embedding_model = lambda _name: FakeEmbeddingModel()

import app as backend_app  # noqa: E402
import chat_service  # noqa: E402
from auth.models import guest_user  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from starlette.datastructures import UploadFile  # noqa: E402
from unittest.mock import patch  # noqa: E402


class PathSecurityTest(unittest.TestCase):
    """验证路径安全模块本身，以及上传和知识库 API 对该模块的真实接入。"""

    def test_rejects_traversal_and_absolute_filenames(self):
        """锁定 path_security.is_safe_filename() 必须拒绝的上传文件名边界。"""
        invalid_names = [
            "../escape.txt",
            "../../escape.txt",
            "/tmp/escape.txt",
        ]

        for filename in invalid_names:
            with self.subTest(filename=filename):
                self.assertFalse(is_safe_filename(filename))

    def test_accepts_english_and_chinese_filenames(self):
        """确认上传安全规则不会误伤 Mini ChatChat 支持的英文和中文文件名。"""
        for filename in ["sample.txt", "项目资料.pdf"]:
            with self.subTest(filename=filename):
                self.assertTrue(is_safe_filename(filename))

    def test_rejects_invalid_kb_names(self):
        """锁定 path_security.is_safe_kb_name() 必须拒绝的知识库名称边界。"""
        invalid_names = [
            "",
            ".",
            "..",
            "../escape",
            "../../escape",
            "/tmp/escape",
            r"C:\temp\escape",
            "parent/child",
            r"parent\child",
        ]

        for kb_name in invalid_names:
            with self.subTest(kb_name=kb_name):
                self.assertFalse(is_safe_kb_name(kb_name))

    def test_accepts_english_and_chinese_kb_names(self):
        """确认知识库安全规则不会破坏原本可创建的英文和中文 KB。"""
        for kb_name in ["product_docs", "产品知识库"]:
            with self.subTest(kb_name=kb_name):
                self.assertTrue(is_safe_kb_name(kb_name))

    def test_safe_join_rejects_escaped_target(self):
        """确认 path_security.safe_join() 会在拼接后再次阻止路径跑出目标目录。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(PathValidationError):
                safe_join(temp_dir, "../escape.txt", field_name="filename")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink is unavailable")
    def test_safe_join_rejects_symlink_outside_root(self):
        """确认 safe_join 会按真实路径拦截指向知识库目录外的 symlink。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "root"
            outside = Path(temp_dir) / "outside"
            root.mkdir()
            outside.mkdir()
            # ``linked`` 本身是合法 kb_name，但它实际指向 outside。这个场景证明
            # 只检查名称不够，还必须由 safe_join 检查文件系统最终访问的位置。
            (root / "linked").symlink_to(outside, target_is_directory=True)

            with self.assertRaises(PathValidationError):
                safe_join(root, "linked", field_name="kb_name")

    def test_upload_routes_return_400_before_file_work(self):
        """确认 app.py 的普通上传和临时上传接口会在业务处理前拒绝危险名称。"""
        invalid_names = [
            "../escape.txt",
            "../../escape.txt",
            "/tmp/escape.txt",
        ]

        with (
            patch.object(backend_app, "require_permission"),
            # get_scoped_kb_service() 会取得 backend/services/kb_service.py 中负责
            # 知识库文件、索引和检索的服务。非法 filename 必须在进入这一层前被
            # 拦截；如果这里真的报错，说明危险名称已经进入业务流程，校验位置太晚。
            patch.object(
                backend_app,
                "get_scoped_kb_service",
                side_effect=AssertionError("invalid filename reached KB service"),
            ),
            TestClient(backend_app.app) as client,
        ):
            for filename in invalid_names:
                with self.subTest(route="upload", filename=filename):
                    response = client.post(
                        "/upload",
                        data={"kb_name": "default"},
                        files={"file": (filename, b"test", "text/plain")},
                    )
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json(), {"detail": "invalid filename"})

                with self.subTest(route="temp_upload", filename=filename):
                    response = client.post(
                        "/temp_upload",
                        files={"file": (filename, b"test", "text/plain")},
                    )
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json(), {"detail": "invalid filename"})

    def test_upload_routes_reject_windows_paths_at_route_boundary(self):
        """直接调用 app.py 上传路由，确认原始 Windows 路径不会绕过 filename 校验。"""
        for route in (backend_app.upload, backend_app.temp_upload):
            upload = UploadFile(
                filename=r"C:\temp\escape.txt",
                file=io.BytesIO(b"test"),
            )
            with (
                self.subTest(route=route.__name__),
                patch.object(backend_app, "require_permission"),
                # TestClient 的 multipart 解析可能先把 Windows 路径改成 basename，
                # 所以这里直接调用 route。知识库处理服务一旦被取得就立即报错，
                # 用来证明 Windows 路径同样在读取、写盘和建索引之前被拒绝。
                patch.object(
                    backend_app,
                    "get_scoped_kb_service",
                    side_effect=AssertionError("invalid filename reached KB service"),
                ),
            ):
                with self.assertRaisesRegex(PathValidationError, "invalid filename"):
                    route_kwargs = {
                        "file": upload,
                        "chunk_size": 300,
                        "chunk_overlap": 50,
                        "current_user": guest_user(),
                    }
                    if route is backend_app.upload:
                        route_kwargs["kb_name"] = "default"
                        route_kwargs["override"] = True
                    asyncio.run(route(**route_kwargs))

    def test_temp_upload_helper_rejects_invalid_name_before_side_effects(self):
        """确认 chat_service.py 的 temp KB 创建函数自身也会先检查 filename。"""
        invalid_names = [
            "../escape.txt",
            "../../escape.txt",
            "/tmp/escape.txt",
            r"C:\temp\escape.txt",
            r"..\escape.txt",
        ]

        # create_temp_kb_from_upload() 位于 backend/chat_service.py，负责保存临时上传、
        # 解析文档并建立 temp KB（只服务当前临时文件问答的知识库）。它随后调用
        # user_scope.py 的 migrate_legacy_demo_files() 迁移旧版 demo 文件。这里让迁移
        # 一旦执行就报错，用来证明危险 filename 在任何迁移或写盘之前已被拒绝，
        # 而不是只依赖 backend/app.py 的 API 路由提前检查。
        with patch.object(
            chat_service,
            "migrate_legacy_demo_files",
            side_effect=AssertionError("invalid filename triggered migration"),
        ):
            for filename in invalid_names:
                with self.subTest(filename=filename):
                    with self.assertRaisesRegex(PathValidationError, "invalid filename"):
                        chat_service.create_temp_kb_from_upload(b"test", filename)

    def test_create_kb_rejects_invalid_names_with_400(self):
        """确认 app.py 的创建知识库接口在建目录和写数据库前拒绝非法 kb_name。"""
        invalid_names = [
            "../escape",
            "../../escape",
            "/tmp/escape",
            r"C:\temp\escape",
            "parent/child",
            r"parent\child",
        ]

        with (
            patch.object(backend_app, "require_permission"),
            # create_kb() 来自 backend/db.py，负责写入知识库记录。这里故意让它一旦
            # 被调用就报错：如果触发，说明非法 kb_name 已越过 API 的路径检查并进入
            # 数据库写入阶段，修复并没有真正卡在业务副作用之前。
            patch.object(
                backend_app,
                "create_kb",
                side_effect=AssertionError("invalid kb_name reached create_kb"),
            ),
            TestClient(backend_app.app) as client,
        ):
            for kb_name in invalid_names:
                with self.subTest(kb_name=kb_name):
                    response = client.post(
                        "/knowledge_bases",
                        json={"kb_name": kb_name},
                    )
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json(), {"detail": "invalid kb_name"})

    def test_create_kb_accepts_chinese_name(self):
        """确认 app.py 仍会用原始中文 kb_name 创建目录和数据库记录。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(backend_app, "require_permission"),
                # get_user_kb_root() 正常会返回当前用户的知识库根目录。这里改为临时
                # 目录，让创建接口真实执行子目录创建，同时不写入现有用户知识库。
                patch.object(backend_app, "get_user_kb_root", return_value=temp_dir),
                patch.object(backend_app, "create_kb") as create_kb,
                TestClient(backend_app.app) as client,
            ):
                response = client.post(
                    "/knowledge_bases",
                    json={"kb_name": "产品知识库"},
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"message": "产品知识库 created"})
            create_kb.assert_called_once_with("产品知识库", user_id=None)
            self.assertTrue((Path(temp_dir) / "产品知识库" / "content").is_dir())


if __name__ == "__main__":
    unittest.main()
