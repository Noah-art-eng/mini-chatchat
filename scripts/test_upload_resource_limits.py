"""为 Upload / ZIP 输入资源限制建立 RED 阶段回归测试。"""

import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# 所有 API、数据库和知识库写入都进入临时 runtime，避免 RED 测试污染真实数据。
TEST_RUNTIME = tempfile.TemporaryDirectory()
os.environ["MINI_CHATCHAT_DB_PATH"] = str(Path(TEST_RUNTIME.name) / "mini.db")
os.environ["MINI_CHATCHAT_DATA_ROOT"] = str(Path(TEST_RUNTIME.name) / "data")
os.environ["MINI_CHATCHAT_UPLOADS_DIR"] = str(Path(TEST_RUNTIME.name) / "uploads")


class FakeEmbeddingModel:
    """避免路径与资源限制测试加载真实 Embedding 模型。"""

    def encode(self, texts):
        """返回足够初始化测试索引的固定向量。"""
        return np.ones((len(texts), 2), dtype="float32")


import services.kb_service as kb_service_module  # noqa: E402

kb_service_module.get_embedding_model = lambda _name: FakeEmbeddingModel()

import app as backend_app  # noqa: E402
import chat_service  # noqa: E402
import resource_limits  # noqa: E402
import services.kb_import_export_service as kb_archive  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class UploadResourceLimitTest(unittest.TestCase):
    """验证普通上传和 temp upload 在进入知识库处理前执行字节限制。"""

    def setUp(self):
        """为每个测试准备互不影响的知识库目录。"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        """清理本测试创建的文件。"""
        self.temp_dir.cleanup()

    def _service(self):
        """提供上传路由需要的最小知识库服务接口。"""
        upload_path = self.root / "uploads"
        content_path = self.root / "content"
        upload_path.mkdir(exist_ok=True)
        content_path.mkdir(exist_ok=True)
        return SimpleNamespace(
            kb_name="default",
            upload_path=str(upload_path),
            content_path=str(content_path),
            save_file_record=Mock(),
        )

    def _post_upload(self, filename, content, service):
        """调用普通上传 API，并隔离与资源限制无关的索引流程。"""
        with (
            patch.object(backend_app, "require_permission"),
            patch.object(backend_app, "get_scoped_kb_service", return_value=service),
            patch.object(backend_app, "process_uploaded_document"),
            patch.object(backend_app, "MAX_DOCUMENT_UPLOAD_BYTES", 8, create=True),
            TestClient(backend_app.app, raise_server_exceptions=False) as client,
        ):
            return client.post(
                "/upload",
                files={"file": (filename, content, "text/plain")},
            )

    def test_normal_upload_allows_small_file(self):
        """小文件应继续进入原有上传流程，避免资源限制误伤正常请求。"""
        response = self._post_upload("small.txt", b"small", self._service())
        self.assertEqual(response.status_code, 200)

    def test_normal_upload_allows_file_at_limit(self):
        """普通上传大小恰好等于限制时必须允许。"""
        response = self._post_upload("exact.txt", b"12345678", self._service())
        self.assertEqual(response.status_code, 200)

    def test_normal_upload_rejects_one_byte_over_before_kb_service(self):
        """超限一字节应返回 413，且不能取得会写盘和重建索引的 KB Service。"""
        with (
            patch.object(backend_app, "require_permission"),
            patch.object(backend_app, "MAX_DOCUMENT_UPLOAD_BYTES", 8, create=True),
            patch.object(
                backend_app,
                "get_scoped_kb_service",
                side_effect=AssertionError("oversized upload reached KB Service"),
            ),
            patch.object(
                backend_app,
                "process_uploaded_document",
                side_effect=AssertionError("oversized upload reached document parsing"),
            ),
            TestClient(backend_app.app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/upload",
                files={"file": ("too-large.txt", b"123456789", "text/plain")},
            )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(list(self.root.rglob("*")), [])

    def test_normal_upload_accepts_chinese_filename(self):
        """中文 filename 应继续通过资源检查和原有路径安全校验。"""
        response = self._post_upload("项目资料.txt", b"small", self._service())
        self.assertEqual(response.status_code, 200)

    def _post_temp_upload(self, content, create_result=None):
        """调用 temp upload API，并替换后续临时知识库创建流程。"""
        result = create_result or {
            "temp_kb_id": "test-temp-kb",
            "message": "uploaded",
        }
        with (
            patch.object(backend_app, "MAX_TEMP_UPLOAD_BYTES", 8, create=True),
            patch.object(backend_app, "create_temp_kb_from_upload", return_value=result),
            TestClient(backend_app.app, raise_server_exceptions=False) as client,
        ):
            return client.post(
                "/temp_upload",
                files={"file": ("临时资料.txt", content, "text/plain")},
            )

    def test_temp_upload_allows_small_file(self):
        """小型临时文件应继续进入 temp KB 创建流程。"""
        response = self._post_temp_upload(b"small")
        self.assertEqual(response.status_code, 200)

    def test_temp_upload_allows_file_at_limit(self):
        """temp upload 大小恰好等于限制时必须允许。"""
        response = self._post_temp_upload(b"12345678")
        self.assertEqual(response.status_code, 200)

    def test_temp_upload_rejects_one_byte_over_without_temp_kb(self):
        """超限 temp upload 应返回 413，且不能创建或遗留 temp KB。"""
        temp_root = Path(TEST_RUNTIME.name) / "data" / "users" / "demo" / "temp"
        before = set(temp_root.rglob("*")) if temp_root.exists() else set()

        with (
            patch.object(backend_app, "MAX_TEMP_UPLOAD_BYTES", 8, create=True),
            patch.object(
                backend_app,
                "create_temp_kb_from_upload",
                side_effect=AssertionError("oversized upload reached temp KB creation"),
            ),
            TestClient(backend_app.app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/temp_upload",
                files={"file": ("too-large.txt", b"123456789", "text/plain")},
            )

        after = set(temp_root.rglob("*")) if temp_root.exists() else set()
        self.assertEqual(response.status_code, 413)
        self.assertEqual(after, before)

    def test_temp_upload_passes_staged_path_and_cleans_it_after_success(self):
        """temp upload 应把文件路径而非完整 bytes 交给临时知识库流程，并在成功后清理。"""
        observed = {}

        def create_from_path(staged_path, filename, **_kwargs):
            observed["path"] = staged_path
            observed["filename"] = filename
            observed["content"] = Path(staged_path).read_bytes()
            return {"temp_kb_id": "test-temp-kb", "message": "uploaded"}

        with (
            patch.object(backend_app, "MAX_TEMP_UPLOAD_BYTES", 8),
            patch.object(
                backend_app,
                "create_temp_kb_from_upload",
                side_effect=create_from_path,
            ),
            TestClient(backend_app.app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/temp_upload",
                files={"file": ("临时资料.txt", b"content", "text/plain")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(observed["path"], str)
        self.assertEqual(observed["filename"], "临时资料.txt")
        self.assertEqual(observed["content"], b"content")
        self.assertFalse(Path(observed["path"]).exists())

    def test_temp_upload_cleans_staged_path_when_temp_kb_creation_fails(self):
        """临时知识库创建失败后，上传阶段生成的 staging 文件也必须删除。"""
        observed = {}

        def fail_from_path(staged_path, _filename, **_kwargs):
            observed["path"] = staged_path
            raise RuntimeError("temp KB failed")

        with (
            patch.object(backend_app, "MAX_TEMP_UPLOAD_BYTES", 8),
            patch.object(
                backend_app,
                "create_temp_kb_from_upload",
                side_effect=fail_from_path,
            ),
            TestClient(backend_app.app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/temp_upload",
                files={"file": ("temp.txt", b"content", "text/plain")},
            )

        self.assertEqual(response.status_code, 500)
        self.assertFalse(Path(observed["path"]).exists())


class RecordingUpload:
    """记录每次 read() 的参数，用来锁定上传必须按固定大小分块读取。"""

    def __init__(self, content):
        """保存待上传内容，并从第一个字节开始模拟读取。"""
        self.content = content
        self.offset = 0
        self.read_sizes = []

    async def read(self, size=None):
        """按调用方给出的大小返回下一块内容，并记录是否出现无参数读取。"""
        self.read_sizes.append(size)
        if size is None:
            raise AssertionError("upload read() was called without a size")
        chunk = self.content[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk


class ResourceLimitConfigTest(unittest.TestCase):
    """验证 ZIP 压缩比配置不能通过特殊浮点值关闭安全检查。"""

    def test_zip_compression_ratio_rejects_invalid_values(self):
        """非数字、非有限值、零和负数都必须在读取配置时立即失败。"""
        variable = "MINI_CHATCHAT_MAX_ZIP_COMPRESSION_RATIO"

        for raw_value in ("abc", "nan", "NaN", "inf", "-inf", "0", "-1"):
            with self.subTest(raw_value=raw_value), patch.dict(
                os.environ,
                {variable: raw_value},
            ):
                with self.assertRaises(ValueError):
                    resource_limits._positive_float_from_env(variable, 100)

    def test_zip_compression_ratio_allows_positive_finite_values(self):
        """正常正数应按原值生效，不应被替换成默认配置。"""
        variable = "MINI_CHATCHAT_MAX_ZIP_COMPRESSION_RATIO"

        for raw_value, expected in (("1", 1.0), ("100", 100.0), ("100.5", 100.5)):
            with self.subTest(raw_value=raw_value), patch.dict(
                os.environ,
                {variable: raw_value},
            ):
                self.assertEqual(
                    resource_limits._positive_float_from_env(variable, 100),
                    expected,
                )


class StreamingUploadTest(unittest.IsolatedAsyncioTestCase):
    """验证统一上传 helper 不构造完整 bytes，并正确管理 staging 文件。"""

    async def asyncSetUp(self):
        """让每个流式上传场景只操作独立临时目录。"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    async def asyncTearDown(self):
        """清理本测试留下的 staging 和目标文件。"""
        self.temp_dir.cleanup()

    async def test_streaming_helper_reads_sized_chunks_and_preserves_content(self):
        """多个小块必须完整落盘，且每次 read() 都带不超过配置值的 size。"""
        upload = RecordingUpload(b"abcdefghij")

        staged = await resource_limits.stage_upload(
            upload,
            max_bytes=10,
            chunk_bytes=3,
            directory=str(self.root),
            suffix=".txt",
            error_message="document upload exceeds configured limit",
        )

        self.assertEqual(Path(staged.path).read_bytes(), b"abcdefghij")
        self.assertEqual(staged.size, 10)
        self.assertTrue(all(size is not None for size in upload.read_sizes))
        self.assertTrue(all(size <= 3 for size in upload.read_sizes))

    async def test_streaming_helper_allows_exact_limit(self):
        """累计字节数等于上限时应成功，而不是误判为超限。"""
        staged = await resource_limits.stage_upload(
            RecordingUpload(b"12345678"),
            max_bytes=8,
            chunk_bytes=3,
            directory=str(self.root),
            error_message="document upload exceeds configured limit",
        )

        self.assertEqual(staged.size, 8)

    async def test_streaming_helper_rejects_over_limit_and_removes_staging(self):
        """累计字节数超限后应立即失败，并删除尚未完成的 staging 文件。"""
        before = set(self.root.iterdir())

        with self.assertRaises(resource_limits.ResourceLimitError):
            await resource_limits.stage_upload(
                RecordingUpload(b"123456789"),
                max_bytes=8,
                chunk_bytes=3,
                directory=str(self.root),
                error_message="document upload exceeds configured limit",
            )

        self.assertEqual(set(self.root.iterdir()), before)

    async def test_streaming_helper_removes_staging_when_write_fails(self):
        """磁盘写入异常不能留下不可用的半截上传文件。"""
        before = set(self.root.iterdir())

        with (
            patch("resource_limits.open", side_effect=OSError("disk full"), create=True),
            self.assertRaises(OSError),
        ):
            await resource_limits.stage_upload(
                RecordingUpload(b"content"),
                max_bytes=20,
                chunk_bytes=3,
                directory=str(self.root),
                error_message="document upload exceeds configured limit",
            )

        self.assertEqual(set(self.root.iterdir()), before)

    async def test_atomic_install_does_not_replace_existing_file_on_copy_failure(self):
        """把 staging 文件复制进目标目录失败时，已有正式文件必须保持原内容。"""
        source = self.root / "source.tmp"
        source.write_bytes(b"new content")
        target = self.root / "target.txt"
        target.write_bytes(b"old content")

        with (
            patch("resource_limits.shutil.copyfileobj", side_effect=OSError("copy failed")),
            self.assertRaises(OSError),
        ):
            resource_limits.install_staged_file(str(source), str(target), chunk_bytes=3)

        self.assertEqual(target.read_bytes(), b"old content")
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), ["source.tmp", "target.txt"])

    async def test_temp_kb_failure_removes_created_temp_directory(self):
        """临时文件解析失败时，应删除本次 UUID 对应的 temp KB 目录和缓存项。"""
        staged_path = self.root / "staged.txt"
        staged_path.write_bytes(b"content")
        temp_root = self.root / "temp-kbs"

        with (
            patch.object(chat_service, "get_temp_root_path", return_value=str(temp_root)),
            patch.object(chat_service, "migrate_legacy_demo_files"),
            patch.object(
                chat_service,
                "parse_file_to_text_file",
                side_effect=RuntimeError("parse failed"),
            ),
            self.assertRaises(RuntimeError),
        ):
            chat_service.create_temp_kb_from_upload(
                str(staged_path),
                "资料.txt",
                user_id=123,
            )

        self.assertEqual(list(temp_root.iterdir()), [])


class ZipResourceLimitTest(unittest.TestCase):
    """验证 ZIP 上传和解压限制在正式 KB 副作用之前生效。"""

    def setUp(self):
        """为每个 ZIP 场景准备独立目录。"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        """清理 ZIP、解压目录和模拟知识库。"""
        self.temp_dir.cleanup()

    def _zip_bytes(self, members, compression=zipfile.ZIP_STORED):
        """用小数据构造 ZIP，边界大小由测试临时调低的限制决定。"""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
            for name, content in members:
                archive.writestr(name, content)
        return buffer.getvalue()

    def _extract(self, payload, **limits):
        """调用现有安全解压入口，并把正式阈值缩小到测试规模。"""
        archive_path = self.root / "archive.zip"
        extract_path = self.root / "extract"
        archive_path.write_bytes(payload)
        extract_path.mkdir(exist_ok=True)

        patches = [
            patch.object(kb_archive, name, value, create=True)
            for name, value in limits.items()
        ]
        for active_patch in patches:
            active_patch.start()
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                kb_archive._safe_extract(archive, str(extract_path))
        finally:
            for active_patch in reversed(patches):
                active_patch.stop()
        return extract_path

    def test_small_zip_reaches_existing_import_flow(self):
        """小型 ZIP 应通过上传大小检查并继续调用现有 import_kb()。"""
        payload = self._zip_bytes([("metadata.json", b"{}")])
        with (
            patch.object(backend_app, "require_permission"),
            patch.object(backend_app, "MAX_ZIP_UPLOAD_BYTES", len(payload), create=True),
            patch.object(
                backend_app,
                "import_kb",
                return_value={"kb_name": "small", "files_count": 0, "chunks_count": 0},
            ) as import_kb,
            TestClient(backend_app.app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/knowledge_bases/import",
                files={"file": ("small.zip", payload, "application/zip")},
            )

        self.assertEqual(response.status_code, 200)
        import_kb.assert_called_once()

    def test_zip_upload_cleans_temporary_file_after_success(self):
        """ZIP 导入成功后也必须删除上传阶段的临时 ZIP。"""
        payload = self._zip_bytes([("metadata.json", b"{}")])
        observed = {}

        def import_from_path(zip_path, **_kwargs):
            observed["path"] = zip_path
            observed["content"] = Path(zip_path).read_bytes()
            return {"kb_name": "small", "files_count": 0, "chunks_count": 0}

        with (
            patch.object(backend_app, "require_permission"),
            patch.object(backend_app, "MAX_ZIP_UPLOAD_BYTES", len(payload)),
            patch.object(backend_app, "import_kb", side_effect=import_from_path),
            TestClient(backend_app.app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/knowledge_bases/import",
                files={"file": ("small.zip", payload, "application/zip")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed["content"], payload)
        self.assertFalse(Path(observed["path"]).exists())

    def test_zip_upload_rejects_one_byte_over_and_cleans_temp_file(self):
        """ZIP 本身超限应返回 413，不进入 import_kb，并清理临时 ZIP。"""
        zip_temp = self.root / "zip-temp"
        zip_temp.mkdir()
        before = set(zip_temp.iterdir())

        with (
            patch.object(backend_app, "require_permission"),
            patch.object(backend_app, "MAX_ZIP_UPLOAD_BYTES", 8, create=True),
            patch.object(
                backend_app,
                "import_kb",
                side_effect=AssertionError("oversized ZIP reached import_kb"),
            ),
            patch.object(tempfile, "tempdir", str(zip_temp)),
            TestClient(backend_app.app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/knowledge_bases/import",
                files={"file": ("too-large.zip", b"123456789", "application/zip")},
            )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(set(zip_temp.iterdir()), before)

    def test_zip_allows_member_count_at_limit(self):
        """非目录 member 数量恰好等于限制时允许解压。"""
        payload = self._zip_bytes([(f"content/{index}.txt", b"") for index in range(3)])
        extract_path = self._extract(payload, MAX_ZIP_MEMBER_COUNT=3)
        self.assertEqual(len(list((extract_path / "content").iterdir())), 3)

    def test_zip_rejects_member_count_over_limit_before_extractall(self):
        """非目录 member 超限时必须在 extractall 和正式 KB 操作前拒绝。"""
        payload = self._zip_bytes([(f"content/{index}.txt", b"") for index in range(4)])
        archive_path = self.root / "many.zip"
        archive_path.write_bytes(payload)

        with (
            patch.object(kb_archive, "MAX_ZIP_MEMBER_COUNT", 3, create=True),
            zipfile.ZipFile(archive_path, "r") as archive,
            patch.object(
                archive,
                "extractall",
                side_effect=AssertionError("member limit checked after extractall"),
            ),
        ):
            with self.assertRaises(ValueError):
                kb_archive._safe_extract(archive, str(self.root / "extract-many"))

    def test_zip_allows_single_member_at_size_limit(self):
        """单个 member 解压大小恰好等于限制时允许。"""
        payload = self._zip_bytes([("content/exact.txt", b"12345678")])
        extract_path = self._extract(payload, MAX_ZIP_MEMBER_BYTES=8)
        self.assertEqual((extract_path / "content" / "exact.txt").read_bytes(), b"12345678")

    def test_zip_rejects_single_member_one_byte_over(self):
        """单个 member 超限一字节时必须拒绝。"""
        payload = self._zip_bytes([("content/large.txt", b"123456789")])
        with self.assertRaises(ValueError):
            self._extract(payload, MAX_ZIP_MEMBER_BYTES=8)

    def test_zip_allows_total_uncompressed_size_at_limit(self):
        """所有 member 解压总量恰好等于限制时允许。"""
        payload = self._zip_bytes([
            ("content/one.txt", b"123456"),
            ("content/two.txt", b"123456"),
        ])
        extract_path = self._extract(payload, MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES=12)
        self.assertTrue((extract_path / "content" / "two.txt").exists())

    def test_zip_rejects_total_uncompressed_size_one_byte_over(self):
        """ZIP 总解压量超限一字节时必须拒绝。"""
        payload = self._zip_bytes([
            ("content/one.txt", b"123456"),
            ("content/two.txt", b"1234567"),
        ])
        with self.assertRaises(ValueError):
            self._extract(payload, MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES=12)

    def test_zip_rejects_high_compression_ratio(self):
        """达到检查门槛且压缩比超过上限的 member 必须作为 ZIP Bomb 拒绝。"""
        payload = self._zip_bytes(
            [("content/repeated.txt", b"A" * 100)],
            compression=zipfile.ZIP_DEFLATED,
        )
        with self.assertRaises(ValueError):
            self._extract(
                payload,
                ZIP_RATIO_MIN_UNCOMPRESSED_BYTES=10,
                MAX_ZIP_COMPRESSION_RATIO=3,
            )

    def test_zip_resource_failure_preserves_existing_kb(self):
        """资源检查失败时不能覆盖目录或删除已有 KB 数据库记录。"""
        user_root = self.root / "user-kbs"
        existing = user_root / "existing"
        existing.mkdir(parents=True)
        sentinel = existing / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")

        payload = self._zip_bytes([
            ("metadata.json", json.dumps({"kb_name": "existing", "files": []})),
            ("content/large.txt", b"123456789"),
        ])
        archive_path = self.root / "override.zip"
        archive_path.write_bytes(payload)

        try:
            with (
                patch.object(kb_archive, "MAX_ZIP_MEMBER_BYTES", 8, create=True),
                patch.object(kb_archive, "get_user_kb_root", return_value=str(user_root)),
                patch.object(
                    kb_archive,
                    "_copy_kb_directories",
                    side_effect=AssertionError("resource check happened after KB replacement"),
                ),
                patch.object(
                    kb_archive,
                    "_reset_kb_records",
                    side_effect=AssertionError("resource check happened after DB deletion"),
                ),
            ):
                with self.assertRaises(ValueError):
                    kb_archive.import_kb(str(archive_path), override=True, user_id=1)
        finally:
            self.assertTrue(sentinel.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_zip_accepts_chinese_kb_and_member_names(self):
        """资源限制不能误伤中文 kb_name 和 ZIP member 名称。"""
        user_root = self.root / "chinese-kbs"
        payload = self._zip_bytes([
            ("metadata.json", json.dumps({"kb_name": "中文知识库", "files": []})),
            ("content/中文资料.txt", "中文内容".encode("utf-8")),
        ])
        archive_path = self.root / "中文导入.zip"
        archive_path.write_bytes(payload)

        service = Mock()
        service.chunks = []
        with (
            patch.object(kb_archive, "get_user_kb_root", return_value=str(user_root)),
            patch.object(kb_archive, "create_kb"),
            patch.object(kb_archive, "MiniKBService", return_value=service),
            patch.object(kb_archive, "_restore_file_metadata"),
        ):
            result = kb_archive.import_kb(str(archive_path), user_id=1)

        self.assertEqual(result["kb_name"], "中文知识库")
        self.assertTrue((user_root / "中文知识库" / "content" / "中文资料.txt").exists())


if __name__ == "__main__":
    unittest.main()
