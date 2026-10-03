import os
import json
import hashlib
import logging
import math
import re
import tempfile
import threading
from collections import Counter
from functools import lru_cache

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from model_config import get_embedding_model_name
from rag import (
    DEFAULT_EMBEDDING_BATCH_SIZE,
    build_faiss_index,
    iter_embedding_batches,
    load_and_split_documents,
    load_and_split_file,
    load_documents,
    split_documents,
)

from db import (
    upsert_file_record,
    delete_file_record,
    list_file_records,
    add_file_doc,
    delete_file_docs,
    sync_kb_file_mappings,
    resolve_user_id,
)
from user_scope import get_user_kb_root, migrate_legacy_demo_files
from path_security import safe_join

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]")
VECTOR_METADATA_FORMAT_VERSION = 1
EMBEDDING_PIPELINE_VERSION = 1
NORMALIZE_EMBEDDINGS = False
_KB_MUTATION_LOCKS = {}
_KB_MUTATION_LOCKS_GUARD = threading.Lock()
logger = logging.getLogger("mini-chatchat")


def get_kb_mutation_lock(user_id, kb_name):
    """返回当前进程内专属于 user + KB 的可重入 mutation 锁。"""
    key = (resolve_user_id(user_id), kb_name)
    with _KB_MUTATION_LOCKS_GUARD:
        return _KB_MUTATION_LOCKS.setdefault(key, threading.RLock())


def _remove_staging_file(path):
    """清理本次索引保存产生的 staging，清理失败不覆盖原始异常。"""
    if not path:
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        pass


@lru_cache(maxsize=None)
def get_embedding_model(model_name: str) -> SentenceTransformer:
    """同一进程复用嵌入模型，避免每个 KB 服务重复加载权重。"""
    return SentenceTransformer(model_name)


class MiniKBService:
    """管理一个用户知识库的文件、文本块、检索索引和持久化状态。

    每个实例只处理一个 user + kb_name，并使用独立目录：
        data/users/{user}/knowledge_bases/{kb_name}/content/
        data/users/{user}/knowledge_bases/{kb_name}/uploads/
        data/users/{user}/knowledge_bases/{kb_name}/vector_store/

    上传、重建和删除共用同一把进程内锁，避免同一知识库的文件、索引和数据库映射
    在并发修改时互相覆盖。初始化时优先加载已有快照；快照不可信时再安全重建。
    """

    def __init__(
        self,
        kb_name: str = "default",
        root_path: str | None = None,
        chunk_size: int = 300,
        chunk_overlap: int = 50,
        user_id=None,
    ):
        """创建只属于一个 user_id 和 kb_name 的知识库服务，并加载可用索引快照。"""
        migrate_legacy_demo_files()
        self.kb_name = kb_name
        self.user_id = user_id
        self.embedding_model_name = get_embedding_model_name()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.mutation_lock = get_kb_mutation_lock(user_id, kb_name)

        self.root_path = root_path or get_user_kb_root(user_id)
        self.kb_path = os.path.join(self.root_path, kb_name)
        self.content_path = os.path.join(self.kb_path, "content")
        self.upload_path = os.path.join(self.kb_path, "uploads")
        self.vector_store_path = os.path.join(self.kb_path, "vector_store")

        for path in (
            self.content_path,
            self.upload_path,
            self.vector_store_path,
        ):
            os.makedirs(path, exist_ok=True)

        # 同一模型名共享权重；KB 仍各自维护独立的文档、索引和 BM25 状态。
        self.model = get_embedding_model(self.embedding_model_name)

        self.documents: list = []
        self.chunks: list = []
        self.index = None
        self.vectors = None
        self.vector_metadata = None
        self._bm25_docs = []
        self._bm25_doc_freqs = Counter()
        self._bm25_idf = {}
        self._bm25_avgdl = 0.0

        chunks_exists = os.path.exists(self.chunks_file_path)

        # 读取和重建都放在同一 KB 锁内。已有快照必须通过数量、结构和 digest 校验；
        # 不能证明一致时宁可重新生成，也不让 chunks 与 FAISS 位置静默错配。
        with self.mutation_lock:
            if chunks_exists:
                try:
                    self.load_vector_store()
                except Exception as exc:
                    logger.warning(
                        "Invalid vector snapshot for kb=%s; rebuilding (%s)",
                        self.kb_name,
                        type(exc).__name__,
                    )
                    self.build_index()
                    self.save_vector_store()
            else:
                self.build_index()
                self.save_vector_store()

    @property
    def index_file_path(self) -> str:
        """返回当前知识库正式 FAISS 索引文件路径。"""
        return os.path.join(self.vector_store_path, "index.faiss")

    @property
    def chunks_file_path(self) -> str:
        """返回与 FAISS 位置一一对应的 chunks.json 路径。"""
        return os.path.join(self.vector_store_path, "chunks.json")

    @property
    def metadata_file_path(self) -> str:
        """返回判断旧向量能否安全复用的 metadata 文件路径。"""
        return os.path.join(self.vector_store_path, "metadata.json")

    def _get_file_chunks(self, filename: str) -> list:
        """从当前内存文本块中筛出指定来源文件的内容。"""
        return [
            chunk
            for chunk in self.chunks
            if chunk.get("source") == filename
        ]
    
    def get_chunk_by_id(self, chunk_id: int) -> dict:
        """按一位起始编号读取文本块，并确认它属于指定文件。"""
        for chunk in self.chunks:
            if chunk.get("chunk_id") == chunk_id:
                return {
                    "chunk_id": chunk.get("chunk_id"),
                    "source": chunk.get("source"),
                    "text": chunk.get("text")
                }

        return {
            "error": "chunk not found"
        }

    def _persist_file_to_db(
        self,
        filename: str,
        file_size: int,
        status: str = "indexed",
        error: str | None = None,
        content_path: str | None = None,
        upload_path: str | None = None,
    ) -> None:
        """把文件大小、处理状态和 chunk_id 映射同步到当前用户的 SQLite 记录。"""
        file_chunks = self._get_file_chunks(filename)

        upsert_file_record(
            self.kb_name,
            filename,
            file_size,
            len(file_chunks),
            status=status,
            error=error,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            content_path=content_path,
            upload_path=upload_path,
            user_id=self.user_id,
        )

        delete_file_docs(self.kb_name, filename, user_id=self.user_id)

        for chunk in file_chunks:
            add_file_doc(
                self.kb_name,
                filename,
                chunk["chunk_id"],
                user_id=self.user_id,
            )

    def sync_files_to_db(self):
        """扫描 content 目录，把现有文件状态同步到数据库。"""
        self.rebuild_and_sync()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def load_documents(self) -> list:
        """兼容旧调用：读取全部 content 文档；生产重建走分批文本块路径。"""
        self.documents = load_documents(self.content_path)
        return self.documents

    def split_documents(self) -> list:
        """兼容旧调用：按当前 chunk_size 和 overlap 切分传入文档。"""
        self.chunks = split_documents(
            self.documents,
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap
        )
        self._build_bm25_index()
        return self.chunks

    def save_vector_store(self) -> None:
        """把 chunks、FAISS 和 metadata 依次写入正式快照文件。

        每个文件先完整写到同目录 staging，再用 `os.replace()` 切换。metadata 最后
        写入并记录正式文件 digest，下一次加载或增量复用时才能确认三者属于同一内容。
        """
        os.makedirs(self.vector_store_path, exist_ok=True)

        # chunks.json 只保存检索和来源展示需要的稳定字段，不写入临时运行状态。
        chunks_metadata = [
            {
                "text": chunk.get("text", ""),
                "source": chunk.get("source", ""),
                "chunk_id": chunk.get("chunk_id"),
            }
            for chunk in self.chunks
        ]

        # 先完整写 staging 并刷到磁盘，再替换正式 chunks.json。写入失败时旧文件仍在。
        chunks_staging = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.vector_store_path,
                prefix="chunks.json.staging-",
                delete=False,
            ) as file:
                chunks_staging = file.name
                json.dump(chunks_metadata, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(chunks_staging, self.chunks_file_path)
            chunks_staging = None
        except Exception:
            _remove_staging_file(chunks_staging)
            raise

        # 空知识库没有 FAISS 索引；清掉旧 index 后仍写 metadata 描述这个空快照。
        if self.index is None:
            if os.path.exists(self.index_file_path):
                os.remove(self.index_file_path)
            self._save_vector_metadata()
            return

        # FAISS 同样写入同目录 staging，完整成功后才替换正式 index.faiss。
        index_staging = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=self.vector_store_path,
                prefix="index.faiss.staging-",
                delete=False,
            ) as file:
                index_staging = file.name
            faiss.write_index(self.index, index_staging)
            with open(index_staging, "rb") as file:
                os.fsync(file.fileno())
            os.replace(index_staging, self.index_file_path)
            index_staging = None
        except Exception:
            _remove_staging_file(index_staging)
            raise
        self._save_vector_metadata()

    def _save_vector_metadata(self) -> None:
        """原子保存增量复用契约；失败时保留已有 metadata。"""
        metadata = dict(self.vector_metadata or {})
        metadata["chunks_sha256"] = self._file_sha256(self.chunks_file_path)
        metadata["index_sha256"] = (
            self._file_sha256(self.index_file_path)
            if os.path.exists(self.index_file_path)
            else None
        )
        metadata_staging = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.vector_store_path,
                prefix="metadata.json.staging-",
                delete=False,
            ) as file:
                metadata_staging = file.name
                json.dump(metadata, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(metadata_staging, self.metadata_file_path)
            metadata_staging = None
            self.vector_metadata = metadata
        except Exception:
            _remove_staging_file(metadata_staging)
            raise

    def _load_vector_metadata(self):
        """读取增量复用 metadata；缺失或损坏只会禁用复用，不影响查询。"""
        try:
            with open(self.metadata_file_path, "r", encoding="utf-8") as file:
                metadata = json.load(file)
        except (OSError, ValueError, TypeError):
            return None
        return metadata if isinstance(metadata, dict) else None

    def _file_sha256(self, path: str) -> str:
        """分块计算持久化文件的 SHA-256，避免校验时整文件进入内存。"""
        digest = hashlib.sha256()
        with open(path, "rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _is_sha256(self, value) -> bool:
        """只接受标准的 64 位小写十六进制 SHA-256。"""
        return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None

    def _metadata_schema_is_valid(self, metadata: dict) -> bool:
        """严格验证 metadata 类型和范围，避免 bool 被当作整数接受。"""
        if type(metadata.get("format_version")) is not int:
            return False
        if metadata.get("format_version") != VECTOR_METADATA_FORMAT_VERSION:
            return False
        model_name = metadata.get("embedding_model")
        if not isinstance(model_name, str) or not model_name.strip():
            return False
        dimension = metadata.get("dimension")
        if type(dimension) is not int or dimension <= 0:
            return False
        if type(metadata.get("normalize_embeddings")) is not bool:
            return False
        pipeline_version = metadata.get("embedding_pipeline_version")
        if type(pipeline_version) is not int or pipeline_version <= 0:
            return False
        chunk_size = metadata.get("chunk_size")
        chunk_overlap = metadata.get("chunk_overlap")
        if type(chunk_size) is not int or chunk_size <= 0:
            return False
        if type(chunk_overlap) is not int or not 0 <= chunk_overlap < chunk_size:
            return False
        if not self._is_sha256(metadata.get("chunks_sha256")):
            return False
        index_sha256 = metadata.get("index_sha256")
        if index_sha256 is not None and not self._is_sha256(index_sha256):
            return False

        sources = metadata.get("sources")
        if not isinstance(sources, dict):
            return False
        for source, source_metadata in sources.items():
            if not isinstance(source, str) or not source:
                return False
            if not isinstance(source_metadata, dict):
                return False
            chunk_count = source_metadata.get("chunk_count")
            if type(chunk_count) is not int or chunk_count < 0:
                return False
            if not self._is_sha256(source_metadata.get("sha256")):
                return False
        return True

    def _snapshot_digests_match(self, metadata: dict, has_index: bool) -> bool:
        """确认 metadata 描述的正是当前正式 chunks/index 文件。"""
        try:
            if self._file_sha256(self.chunks_file_path) != metadata["chunks_sha256"]:
                return False
            if has_index:
                expected = metadata.get("index_sha256")
                return (
                    self._is_sha256(expected)
                    and os.path.exists(self.index_file_path)
                    and self._file_sha256(self.index_file_path) == expected
                )
            return metadata.get("index_sha256") is None and not os.path.exists(
                self.index_file_path
            )
        except OSError:
            return False

    def load_vector_store(self) -> None:
        """加载磁盘快照，并在投入检索前验证 chunks、FAISS 和 metadata 一致。"""
        # chunks 是取回原文和来源的基准，后面的 FAISS position 必须与其下标一致。
        with open(self.chunks_file_path, "r", encoding="utf-8") as file:
            self.chunks = json.load(file)

        # 空快照允许没有 index，但如果旧 index 仍含向量就说明持久化状态不一致。
        if not self.chunks:
            if os.path.exists(self.index_file_path):
                loaded_index = faiss.read_index(self.index_file_path)
                if loaded_index.ntotal != 0:
                    raise ValueError("FAISS index and chunks count mismatch")
            self.index = None
            self.vectors = None
            self.documents = []
            self.vector_metadata = self._load_vector_metadata()
            if os.path.exists(self.metadata_file_path):
                if (
                    self.vector_metadata is None
                    or not self._metadata_schema_is_valid(self.vector_metadata)
                    or not self._snapshot_digests_match(
                        self.vector_metadata,
                        has_index=False,
                    )
                ):
                    raise ValueError("vector snapshot metadata is invalid")
            self._build_bm25_index()
            return

        # 非空 chunks 必须同时有等量 FAISS 向量，否则不能冒险投入检索。
        if not os.path.exists(self.index_file_path):
            raise ValueError("FAISS index is missing for non-empty chunks")

        self.index = faiss.read_index(self.index_file_path)
        self.vectors = None
        if self.index.ntotal != len(self.chunks):
            raise ValueError("FAISS index and chunks count mismatch")

        # metadata 存在时继续校验字段和 SHA-256，防止同数量的不同代文件静默配对。
        self.documents = []
        self.vector_metadata = self._load_vector_metadata()
        if os.path.exists(self.metadata_file_path):
            if (
                self.vector_metadata is None
                or not self._metadata_schema_is_valid(self.vector_metadata)
                or not self._snapshot_digests_match(
                    self.vector_metadata,
                    has_index=True,
                )
            ):
                raise ValueError("vector snapshot metadata is invalid")
        self._build_bm25_index()

    def build_index(self) -> None:
        """从 content 文本重新生成文本块、BM25 状态和 FAISS 向量索引。

        文件按稳定顺序切块，embedding 按批次写入 IndexFlatL2。完成后只更新内存状态；
        调用方随后进入 `save_vector_store()` 落盘，并在需要时同步数据库文件映射。
        """
        try:
            all_files = os.listdir(self.content_path)
        except FileNotFoundError:
            all_files = []

        txt_files = [f for f in all_files if f.endswith(".txt")]

        # rebuild 从 content 文件滑动读取并直接生成最终文本块，避免同时持有完整正文
        # 和完整文本块两份大数据。接下来先建立 BM25，再分批写入 FAISS。
        self.documents = []
        self.chunks = load_and_split_documents(
            self.content_path,
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap,
        )
        self._build_bm25_index()

        if self.chunks:
            # build_faiss_index() 会按批次计算 embedding，并依次加入 IndexFlatL2；
            # 文本块顺序与 FAISS 位置保持一致，检索结果才能按下标取回原文。
            self.index, self.vectors = build_faiss_index(
                self.chunks, self.model
            )
        else:
            self.index = None
            self.vectors = None
            if txt_files:
                logger.warning(
                    "Knowledge base %s has %d text file(s) but produced no chunks",
                    self.kb_name,
                    len(txt_files),
                )

        self.vector_metadata = self._build_vector_metadata()

    def _content_sources(self) -> list[str]:
        """返回参与索引的 content 文本文件，并保持全量 rebuild 的排序。"""
        return sorted(
            filename
            for filename in os.listdir(self.content_path)
            if filename.endswith(".txt")
        )

    def _source_sha256(self, source: str) -> str:
        """对实际进入 Chunk 流程的 content bytes 计算 SHA-256。"""
        return self._file_sha256(os.path.join(self.content_path, source))

    def _model_dimension(self):
        """读取当前模型声明的向量维度；无法确认时禁止复用。"""
        getter = getattr(self.model, "get_sentence_embedding_dimension", None)
        if not callable(getter):
            return None
        dimension = getter()
        if type(dimension) is not int or dimension <= 0:
            return None
        return dimension

    def _build_vector_metadata(self) -> dict:
        """根据当前索引和 content 构造下一次增量判断所需的最小契约。"""
        counts = Counter(chunk.get("source") for chunk in self.chunks)
        dimension = int(self.index.d) if self.index is not None else self._model_dimension()
        return {
            "format_version": VECTOR_METADATA_FORMAT_VERSION,
            "embedding_model": getattr(
                self,
                "embedding_model_name",
                get_embedding_model_name(),
            ),
            "dimension": dimension,
            "normalize_embeddings": NORMALIZE_EMBEDDINGS,
            "embedding_pipeline_version": EMBEDDING_PIPELINE_VERSION,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "sources": {
                source: {
                    "sha256": self._source_sha256(source),
                    "chunk_count": counts.get(source, 0),
                }
                for source in self._content_sources()
            },
        }

    def _load_reusable_snapshot(self):
        """从磁盘读取并严格校验旧 Chunk、向量和 metadata。"""
        # 增量重建只有在模型、维度、分块参数和文件摘要全部兼容时才复用旧向量。
        # 任一字段无法确认就返回 None，让上层退回全量重建。
        metadata = self._load_vector_metadata()
        if metadata is None or not self._metadata_schema_is_valid(metadata):
            return None

        expected = {
            "format_version": VECTOR_METADATA_FORMAT_VERSION,
            "embedding_model": self.embedding_model_name,
            "normalize_embeddings": NORMALIZE_EMBEDDINGS,
            "embedding_pipeline_version": EMBEDDING_PIPELINE_VERSION,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
        }
        if any(metadata.get(key) != value for key, value in expected.items()):
            return None

        model_dimension = self._model_dimension()
        if model_dimension is None or metadata.get("dimension") != model_dimension:
            return None

        try:
            with open(self.chunks_file_path, "r", encoding="utf-8") as file:
                old_chunks = json.load(file)
            old_index = (
                faiss.read_index(self.index_file_path)
                if os.path.exists(self.index_file_path)
                else None
            )
        except (OSError, ValueError, TypeError, RuntimeError):
            return None

        if not isinstance(old_chunks, list):
            return None
        if old_chunks:
            if old_index is None or old_index.ntotal != len(old_chunks):
                return None
            if int(old_index.d) != model_dimension:
                return None
        elif old_index is not None and old_index.ntotal != 0:
            return None

        if not self._snapshot_digests_match(
            metadata,
            has_index=bool(old_chunks),
        ):
            return None

        sources_metadata = metadata.get("sources")
        if not isinstance(sources_metadata, dict):
            return None

        groups = {}
        previous_source = None
        for position, chunk in enumerate(old_chunks):
            if not isinstance(chunk, dict):
                return None
            source = chunk.get("source")
            if not isinstance(source, str) or chunk.get("chunk_id") != position + 1:
                return None
            if source != previous_source and source in groups:
                return None
            group = groups.setdefault(source, {"start": position, "chunks": []})
            group["chunks"].append(chunk)
            previous_source = source

        positive_sources = {
            source
            for source, source_metadata in sources_metadata.items()
            if isinstance(source_metadata, dict)
            and source_metadata.get("chunk_count", 0) > 0
        }
        if set(groups) != positive_sources:
            return None
        for source, group in groups.items():
            source_metadata = sources_metadata.get(source)
            if source_metadata.get("chunk_count") != len(group["chunks"]):
                return None

        return metadata, old_chunks, old_index, groups

    def _add_vectors(self, index, vectors):
        """校验向量形状后按原顺序加入新的 IndexFlatL2。"""
        vectors = np.asarray(vectors, dtype="float32")
        if vectors.ndim != 2:
            raise ValueError("embedding vectors must be a 2D array")
        if index is None:
            index = faiss.IndexFlatL2(vectors.shape[1])
        if vectors.shape[1] != index.d:
            raise ValueError("embedding vector dimension mismatch")
        index.add(vectors)
        return index

    def _build_incremental_index(self) -> bool:
        """复用未变化 source 的旧向量，并只为变化 source 调用模型。"""
        # 先加载通过摘要和结构校验的旧快照。旧格式、损坏文件或配置变化都会返回
        # False，由 rebuild_index() 改走完整 build_index()，不会冒险复用未知向量。
        snapshot = self._load_reusable_snapshot()
        if snapshot is None:
            return False

        metadata, _, old_index, groups = snapshot
        new_chunks = []
        new_index = None

        # 按稳定文件顺序重新组装索引。未变化文件直接重建旧向量，变化或新增文件才
        # 重新切块和计算 embedding；已经删除的文件不会出现在新循环中。
        for source in self._content_sources():
            source_hash = self._source_sha256(source)
            source_metadata = metadata["sources"].get(source)
            group = groups.get(source)

            if (
                group is not None
                and source_metadata is not None
                and source_metadata.get("sha256") == source_hash
            ):
                source_chunks = [dict(chunk) for chunk in group["chunks"]]
                count = len(source_chunks)
                if count:
                    vectors = old_index.reconstruct_n(group["start"], count)
                    vectors = np.asarray(vectors, dtype="float32")
                    if vectors.shape != (count, old_index.d):
                        return False
                    new_index = self._add_vectors(new_index, vectors)
            else:
                source_chunks = load_and_split_file(
                    os.path.join(self.content_path, source),
                    source,
                    chunk_size=self.chunk_size,
                    overlap=self.chunk_overlap,
                )
                for vectors in iter_embedding_batches(
                    source_chunks,
                    self.model,
                    batch_size=DEFAULT_EMBEDDING_BATCH_SIZE,
                ):
                    new_index = self._add_vectors(new_index, vectors)

            # 无论向量来自复用还是重算，chunk_id 都按当前最终顺序重新编号，保证
            # chunks.json、FAISS 位置和数据库 file_doc 映射继续一一对应。
            for chunk in source_chunks:
                chunk["chunk_id"] = len(new_chunks) + 1
                new_chunks.append(chunk)

        if new_index is not None and new_index.ntotal != len(new_chunks):
            return False

        # 新索引数量必须与文本块数量一致。确认后再替换内存状态并重建 BM25；
        # rebuild_index() 随后才把完整快照写入磁盘。
        self.documents = []
        self.chunks = new_chunks
        self.index = new_index
        self.vectors = None
        self._build_bm25_index()
        self.vector_metadata = self._build_vector_metadata()
        return True

    def _tokenize_for_bm25(self, text: str) -> list[str]:
        """把文本转成小写词元，供当前轻量 BM25 统计使用。"""
        return TOKEN_PATTERN.findall((text or "").lower())

    def _build_bm25_index(self) -> None:
        """根据全部文本块重建 BM25 的词频、IDF 和平均长度。

        BM25 需要看到整个文本块集合才能计算文档频率，因此索引重建时仍集中构造
        这部分统计。完成后 search_docs() 才能走关键词候选路线。
        """
        self._bm25_docs = []
        self._bm25_doc_freqs = Counter()
        self._bm25_idf = {}
        self._bm25_avgdl = 0.0

        if not self.chunks:
            return

        total_length = 0

        # 第一遍记录每个文本块的词频，同时统计一个词出现于多少个文本块。
        for chunk in self.chunks:
            tokens = self._tokenize_for_bm25(chunk.get("text", ""))
            token_counts = Counter(tokens)
            total_length += len(tokens)

            self._bm25_docs.append({
                "counts": token_counts,
                "length": len(tokens),
            })

            for token in token_counts:
                self._bm25_doc_freqs[token] += 1

        doc_count = len(self._bm25_docs)
        self._bm25_avgdl = total_length / doc_count if doc_count else 0.0

        # 文档频率转换成 IDF；越少见的词在关键词检索中权重越高。
        for token, doc_freq in self._bm25_doc_freqs.items():
            self._bm25_idf[token] = math.log(
                1 + (doc_count - doc_freq + 0.5) / (doc_freq + 0.5)
            )

    def _bm25_score(self, query_tokens: list[str], chunk_index: int) -> float:
        """计算一个文本块对查询词的 BM25 分数；分数越高表示关键词越相关。"""
        if not query_tokens or not self._bm25_docs:
            return 0.0

        doc = self._bm25_docs[chunk_index]
        doc_length = doc["length"]

        if doc_length == 0 or self._bm25_avgdl == 0:
            return 0.0

        k1 = 1.5
        b = 0.75
        score = 0.0

        for token in query_tokens:
            term_frequency = doc["counts"].get(token, 0)

            if term_frequency == 0:
                continue

            idf = self._bm25_idf.get(token, 0.0)
            denominator = (
                term_frequency
                + k1 * (1 - b + b * doc_length / self._bm25_avgdl)
            )
            score += idf * (term_frequency * (k1 + 1)) / denominator

        return score

    def _metadata_matches(self, chunk: dict, metadata_filter: dict | None) -> bool:
        """检查文本块是否满足本次来源文件过滤条件。"""
        if not metadata_filter:
            return True

        source_filter = (
            metadata_filter.get("source")
            or metadata_filter.get("file_name")
            or metadata_filter.get("filename")
        )

        if source_filter and chunk.get("source") != source_filter:
            return False

        return True

    def _filtered_chunk_indexes(self, metadata_filter: dict | None) -> list[int]:
        """返回本次 metadata_filter 允许参与检索的文本块编号。"""
        return [
            index
            for index, chunk in enumerate(self.chunks)
            if self._metadata_matches(chunk, metadata_filter)
        ]

    def _bm25_candidates(
        self,
        query: str,
        candidate_k: int,
        allowed_indexes: set[int],
    ) -> dict[int, float]:
        """只在允许范围内计算 BM25，并保留得分最高的 candidate_k 个候选。"""
        query_tokens = self._tokenize_for_bm25(query)

        if not query_tokens:
            return {}

        scored = []

        for chunk_index in allowed_indexes:
            score = self._bm25_score(query_tokens, chunk_index)

            if score > 0:
                scored.append((chunk_index, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return dict(scored[:candidate_k])

    def _vector_candidates(
        self,
        query: str,
        candidate_k: int,
        score_threshold: float,
        allowed_indexes: set[int],
        metadata_filter: dict | None = None,
    ) -> dict[int, float]:
        """执行 Hybrid Search 中的 FAISS 向量召回。

        `search_docs()` 把 query 和候选范围交给这里。本函数把问题转换成向量，使用
        IndexFlatL2 找出相近的文本块，再把 vector_candidates 返回给 `search_docs()`。
        """
        if self.index is None or not self.chunks:
            return {}

        # 第一步把用户问题 query 交给 embedding 模型，得到可供 FAISS 搜索的向量。
        query_vector = self.model.encode([query])
        query_vector = np.array(query_vector).astype("float32")

        # search_k 是本次实际让 FAISS 搜多少个。没有 metadata_filter 时，只需搜索
        # candidate_k 个；有过滤条件时，当前索引不能直接按 allowed_indexes 搜索，
        # 所以先扩大到全部文本块，再在下面过滤，避免漏掉指定文件中的相关内容。
        search_k = len(self.chunks) if metadata_filter else candidate_k

        # 接下来进入 FAISS IndexFlatL2。indexes 是命中的文本块编号，distances 是
        # 相同位置对应的 L2 距离；L2 距离越小，表示向量越相似。
        distances, indexes = self.index.search(query_vector, search_k)
        candidates = {}

        # 下面依次清理 FAISS 返回值：-1 表示没有有效结果；不在 allowed_indexes 中的
        # 文本块不属于本次检索范围；超过 score_threshold 的结果距离太远。这里的
        # score_threshold 实际是 L2 距离阈值，因此数值越小越严格。
        for i, raw_index in enumerate(indexes[0]):
            chunk_index = int(raw_index)

            if chunk_index == -1:
                continue

            if chunk_index not in allowed_indexes:
                continue

            distance = float(distances[0][i])

            if distance > score_threshold:
                continue

            candidates[chunk_index] = distance

        return candidates

    def _format_search_result(
        self,
        chunk_index: int,
        vector_distance: float | None,
        bm25_score: float,
        hybrid_score: float,
    ) -> dict:
        """把文本块、两路分数和综合分整理成对外检索结果。"""
        chunk = self.chunks[chunk_index]

        return {
            "chunk": chunk.get("text", ""),
            "source": chunk.get("source", ""),
            "distance": vector_distance,
            "vector_distance": vector_distance,
            "bm25_score": bm25_score,
            "hybrid_score": hybrid_score,
            "chunk_id": chunk.get("chunk_id"),
        }

    def _dedup_key(self, result: dict) -> tuple:
        """优先用来源与 chunk_id 标识结果；旧数据缺少编号时回退到文本摘要。"""
        source = result.get("source") or ""
        chunk_id = result.get("chunk_id")

        if chunk_id is not None:
            return ("source_chunk_id", source, chunk_id)

        chunk_text = result.get("chunk") or ""
        chunk_hash = hashlib.sha256(
            chunk_text.encode("utf-8")
        ).hexdigest()
        return ("source_chunk_hash", source, chunk_hash)

    def _deduplicate_results(self, results: list[dict]) -> list[dict]:
        # 混合检索候选可能指向同一 source/chunk，只保留综合分最高的一项。
        """合并两路召回中的同一文本块，保留综合分最高项并重新编号。"""
        deduped_by_key = {}

        for result in results:
            key = self._dedup_key(result)
            existing = deduped_by_key.get(key)

            if (
                existing is None
                or result.get("hybrid_score", 0) > existing.get("hybrid_score", 0)
            ):
                deduped_by_key[key] = result

        deduped = list(deduped_by_key.values())
        deduped.sort(
            key=lambda item: item.get("hybrid_score", 0),
            reverse=True,
        )

        for index, result in enumerate(deduped, start=1):
            result["id"] = index

        return deduped

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rebuild_index(self) -> None:
        """优先复用兼容旧向量，无法证明兼容时执行保守的全量 rebuild。"""
        with self.mutation_lock:
            # 增量路径只有在旧快照可证明兼容时返回 True，否则完整重算全部文本块。
            if not self._build_incremental_index():
                self.build_index()
            # 内存中的 chunks、FAISS、BM25 全部完成后再写正式快照。
            self.save_vector_store()

    def _sync_current_mappings(self, file_overrides=None) -> None:
        """用当前最终 chunks 在一个事务内刷新整个 KB 的文件映射。"""
        overrides = file_overrides or {}
        files = []
        for filename in sorted(os.listdir(self.content_path)):
            if not filename.endswith(".txt"):
                continue
            files.append({
                "filename": filename,
                "size": os.path.getsize(os.path.join(self.content_path, filename)),
                "chunk_ids": [
                    chunk["chunk_id"]
                    for chunk in self.chunks
                    if chunk.get("source") == filename
                ],
                "metadata": overrides.get(filename, {}),
            })
        sync_kb_file_mappings(
            self.kb_name,
            files,
            user_id=self.user_id,
        )

    def rebuild_and_sync(self, file_overrides=None) -> None:
        """在同一 KB 锁内完成全量 rebuild、落盘和数据库映射同步。"""
        with self.mutation_lock:
            # 文件快照成功落盘后才同步 SQLite 映射，锁覆盖两步，避免同一进程中的
            # 上传、删除和重建交错。它不提供跨进程或跨 SQLite/文件系统的事务。
            self.rebuild_index()
            self._sync_current_mappings(file_overrides=file_overrides)

    def search_docs(
        self,
        query: str,
        top_k: int = 3,
        score_threshold: float = 0.8,
        metadata_filter: dict | None = None,
    ) -> list:
        """知识库 Hybrid Search 的入口，最终返回最多 top_k 个结果。

        `run_kb_chat()` 把用户问题交给这里。本函数先确定允许检索的文本块范围，
        再依次取得 FAISS 和 BM25 候选。两路召回完成后，程序回到这里继续处理结果。
        """
        if self.index is None or not self.chunks:
            return []

        # allowed_indexes 是本次允许参与检索的文本块编号。默认包含整个知识库；
        # metadata_filter 存在时，只保留指定范围。后面的两路召回都使用这个范围。
        allowed_indexes = set(self._filtered_chunk_indexes(metadata_filter))

        if not allowed_indexes:
            return []

        # top_k 是最终希望返回多少条。candidate_k 是 FAISS 和 BM25 各自先找多少个
        # 候选。这里先扩大候选池，但不超过本次实际允许检索的文本块数量。
        candidate_k = min(
            len(allowed_indexes),
            max(top_k * 4, 10),
        )

        # 程序先进入 _vector_candidates() 做 FAISS 向量召回。返回的
        # vector_candidates 是“文本块编号 -> L2 距离”。回到这里后，再进入
        # _bm25_candidates() 做 BM25 关键词召回。
        vector_candidates = self._vector_candidates(
            query,
            candidate_k,
            score_threshold,
            allowed_indexes,
            metadata_filter=metadata_filter,
        )
        bm25_candidates = self._bm25_candidates(
            query,
            candidate_k,
            allowed_indexes,
        )
        candidate_indexes = set(vector_candidates) | set(bm25_candidates)

        if not candidate_indexes:
            return []

        max_bm25 = max(bm25_candidates.values(), default=0.0)
        scored = []

        for chunk_index in candidate_indexes:
            vector_distance = vector_candidates.get(chunk_index)
            vector_score = (
                1 / (1 + vector_distance)
                if vector_distance is not None
                else 0.0
            )
            bm25_score = bm25_candidates.get(chunk_index, 0.0)
            bm25_normalized = bm25_score / max_bm25 if max_bm25 else 0.0
            hybrid_score = 0.65 * vector_score + 0.35 * bm25_normalized

            scored.append((
                chunk_index,
                vector_distance,
                bm25_score,
                hybrid_score,
            ))

        results = [
            self._format_search_result(
                chunk_index,
                vector_distance=vector_distance,
                bm25_score=bm25_score,
                hybrid_score=hybrid_score,
            )
            for (
                chunk_index,
                vector_distance,
                bm25_score,
                hybrid_score,
            ) in scored
        ]
        results = self._deduplicate_results(results)

        return results[:top_k]

    def get_stats(self) -> dict:
        """Return KB metadata shown in the frontend stats panel."""
        file_count = sum(
            1 for f in os.listdir(self.content_path)
            if f.endswith(".txt")
        )
        return {
            "file_count": file_count,
            "chunk_count": len(self.chunks),
            "embedding_model": self.embedding_model_name,
        }

    def list_documents(self) -> list:
        """合并数据库文件状态与磁盘现状，返回知识库页面需要的文件列表。"""
        return list_file_records(self.kb_name, user_id=self.user_id)

    def delete_document(self, filename: str) -> dict:
        """
        Delete a document from the KB and rebuild the index.
        Returns a result dict suitable for passing straight back to the client.
        """
        with self.mutation_lock:
            path = safe_join(self.content_path, filename, field_name="filename")

            if not os.path.exists(path):
                return {"error": "file not found"}

            os.remove(path)

            delete_file_record(self.kb_name, filename, user_id=self.user_id)
            delete_file_docs(self.kb_name, filename, user_id=self.user_id)
            self.rebuild_and_sync()

        return {"message": f"{filename} deleted"}

    def save_file_record(
        self,
        filename,
        file_size,
        status="indexed",
        error=None,
        content_path=None,
        upload_path=None,
    ):
        """保存单个文件的状态和 chunk 映射，供兼容上传流程使用。"""
        self._persist_file_to_db(
            filename,
            file_size,
            status=status,
            error=error,
            content_path=content_path,
            upload_path=upload_path,
        )
