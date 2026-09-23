import os
import json
import hashlib
import math
import re
from collections import Counter
from functools import lru_cache

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from model_config import get_embedding_model_name
from rag import load_documents, split_documents, build_faiss_index

from db import (
    upsert_file_record,
    delete_file_record,
    list_file_records,
    add_file_doc,
    delete_file_docs
)
from user_scope import get_user_kb_root, migrate_legacy_demo_files

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]")


@lru_cache(maxsize=None)
def get_embedding_model(model_name: str) -> SentenceTransformer:
    """同一进程复用嵌入模型，避免每个 KB 服务重复加载权重。"""
    return SentenceTransformer(model_name)


class MiniKBService:
    """
    Service layer that owns all knowledge-base state:
    raw documents, chunk list, FAISS index, and the embedding model.

    Directory layout (ChatChat-style):
        data/users/{user}/knowledge_bases/{kb_name}/content/
        data/users/{user}/knowledge_bases/{kb_name}/uploads/
        data/users/{user}/knowledge_bases/{kb_name}/vector_store/

    app.py should only call public methods on this class and never
    touch the directory paths or in-memory state directly.
    """

    def __init__(
        self,
        kb_name: str = "default",
        root_path: str | None = None,
        chunk_size: int = 300,
        chunk_overlap: int = 50,
        user_id=None,
    ):
        """负责 __init__ 的函数职责。"""
        migrate_legacy_demo_files()
        self.kb_name = kb_name
        self.user_id = user_id
        self.embedding_model_name = get_embedding_model_name()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Directory paths
        self.root_path = root_path or get_user_kb_root(user_id)
        self.kb_path = os.path.join(self.root_path, kb_name)
        self.content_path = os.path.join(self.kb_path, "content")
        self.upload_path = os.path.join(self.kb_path, "uploads")
        self.vector_store_path = os.path.join(self.kb_path, "vector_store")

        # Create all directories on first use
        for path in (
            self.content_path,
            self.upload_path,
            self.vector_store_path,
        ):
            os.makedirs(path, exist_ok=True)

        # 同一模型名共享权重；KB 仍各自维护独立的文档、索引和 BM25 状态。
        self.model = get_embedding_model(self.embedding_model_name)

        # In-memory state; rebuilt whenever the KB changes
        self.documents: list = []
        self.chunks: list = []
        self.index = None
        self.vectors = None
        self._bm25_docs = []
        self._bm25_doc_freqs = Counter()
        self._bm25_idf = {}
        self._bm25_avgdl = 0.0

        index_exists = os.path.exists(self.index_file_path)
        chunks_exists = os.path.exists(self.chunks_file_path)

        if index_exists and chunks_exists:
            self.load_vector_store()
        else:
            self.build_index()
            self.save_vector_store()

    @property
    def index_file_path(self) -> str:
        """负责 index_file_path 的函数职责。"""
        return os.path.join(self.vector_store_path, "index.faiss")

    @property
    def chunks_file_path(self) -> str:
        """负责 chunks_file_path 的函数职责。"""
        return os.path.join(self.vector_store_path, "chunks.json")

    def _get_file_chunks(self, filename: str) -> list:
        """负责 _get_file_chunks 的函数职责。"""
        return [
            chunk
            for chunk in self.chunks
            if chunk.get("source") == filename
        ]
    
    def get_chunk_by_id(self, chunk_id: int) -> dict:
        """负责 get_chunk_by_id 的函数职责。"""
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
        """Write knowledge_file + file_doc records for one content file."""
        file_chunks = self._get_file_chunks(filename)

        print(f"[SYNC] {filename} -> {len(file_chunks)} chunks")

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
        """负责 sync_files_to_db 的函数职责。"""
        self.rebuild_index()

        for filename in sorted(os.listdir(self.content_path)):
            if not filename.endswith(".txt"):
                continue

            path = os.path.join(self.content_path, filename)
            file_size = os.path.getsize(path)
            self._persist_file_to_db(filename, file_size)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def load_documents(self) -> list:
        """Read all .txt files from the content directory."""
        self.documents = load_documents(self.content_path)
        return self.documents

    def split_documents(self) -> list:
        """Split raw documents into fixed-size overlapping chunks."""
        self.chunks = split_documents(
            self.documents,
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap
        )
        self._build_bm25_index()
        return self.chunks

    def save_vector_store(self) -> None:
        """Persist the FAISS index and chunk metadata to vector_store."""
        os.makedirs(self.vector_store_path, exist_ok=True)

        chunks_metadata = [
            {
                "text": chunk.get("text", ""),
                "source": chunk.get("source", ""),
                "chunk_id": chunk.get("chunk_id"),
            }
            for chunk in self.chunks
        ]

        with open(self.chunks_file_path, "w", encoding="utf-8") as file:
            json.dump(chunks_metadata, file, ensure_ascii=False, indent=2)

        if self.index is None:
            if os.path.exists(self.index_file_path):
                os.remove(self.index_file_path)
            print("[KBService] No FAISS index to save")
            return

        faiss.write_index(self.index, self.index_file_path)
        print(f"[KBService] FAISS index saved: {self.index_file_path}")

    def load_vector_store(self) -> None:
        """Load the FAISS index and chunk metadata from vector_store."""
        self.index = faiss.read_index(self.index_file_path)
        self.vectors = None

        with open(self.chunks_file_path, "r", encoding="utf-8") as file:
            self.chunks = json.load(file)

        self.documents = []
        self._build_bm25_index()

        print(
            f"[KBService] FAISS index loaded "
            f"({self.index.ntotal} vectors) | chunks={len(self.chunks)}"
        )

    def build_index(self) -> None:
        """Load documents → split → build FAISS index from scratch."""
        print(f"[KBService] build_index called | kb={self.kb_name}")
        print(f"[KBService] content_path = {os.path.abspath(self.content_path)}")

        try:
            all_files = os.listdir(self.content_path)
        except FileNotFoundError:
            all_files = []

        txt_files = [f for f in all_files if f.endswith(".txt")]
        print(f"[KBService] files in content_path: {txt_files}")

        self.load_documents()
        print(f"[KBService] documents loaded: {len(self.documents)}")

        self.split_documents()
        print(f"[KBService] chunks produced: {len(self.chunks)}")

        if self.chunks:
            self.index, self.vectors = build_faiss_index(
                self.chunks, self.model
            )
            print(f"[KBService] FAISS index built ({self.index.ntotal} vectors)")
        else:
            self.index = None
            self.vectors = None
            if txt_files:
                print(
                    f"[KBService] WARNING: {len(txt_files)} .txt file(s) found "
                    "but 0 chunks produced — files may be empty."
                )
            self._build_bm25_index()

    def _tokenize_for_bm25(self, text: str) -> list[str]:
        """负责 _tokenize_for_bm25 的函数职责。"""
        return TOKEN_PATTERN.findall((text or "").lower())

    def _build_bm25_index(self) -> None:
        """Build lightweight BM25 statistics for current chunks."""
        self._bm25_docs = []
        self._bm25_doc_freqs = Counter()
        self._bm25_idf = {}
        self._bm25_avgdl = 0.0

        if not self.chunks:
            return

        total_length = 0

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

        for token, doc_freq in self._bm25_doc_freqs.items():
            self._bm25_idf[token] = math.log(
                1 + (doc_count - doc_freq + 0.5) / (doc_freq + 0.5)
            )

    def _bm25_score(self, query_tokens: list[str], chunk_index: int) -> float:
        """负责 _bm25_score 的函数职责。"""
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
        """负责 _metadata_matches 的函数职责。"""
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
        """负责 _filtered_chunk_indexes 的函数职责。"""
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
        """负责 _bm25_candidates 的函数职责。"""
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
        """负责 _vector_candidates 的函数职责。"""
        if self.index is None or not self.chunks:
            return {}

        query_vector = self.model.encode([query])
        query_vector = np.array(query_vector).astype("float32")
        search_k = len(self.chunks) if metadata_filter else candidate_k
        distances, indexes = self.index.search(query_vector, search_k)
        candidates = {}

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
        result_id: int,
        vector_distance: float | None,
        bm25_score: float,
        hybrid_score: float,
    ) -> dict:
        """负责 _format_search_result 的函数职责。"""
        chunk = self.chunks[chunk_index]

        return {
            "id": result_id,
            "chunk": chunk.get("text", ""),
            "source": chunk.get("source", ""),
            "distance": vector_distance,
            "vector_distance": vector_distance,
            "bm25_score": bm25_score,
            "hybrid_score": hybrid_score,
            "chunk_id": chunk.get("chunk_id"),
        }

    def _dedup_key(self, result: dict) -> tuple:
        """负责 _dedup_key 的函数职责。"""
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
        """负责 _deduplicate_results 的函数职责。"""
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
        """Full re-index after any document change (upload / delete)."""
        self.build_index()
        self.save_vector_store()

    def search_docs(
        self,
        query: str,
        top_k: int = 3,
        score_threshold: float = 0.8,
        metadata_filter: dict | None = None,
    ) -> list:
        """
        Hybrid-search the knowledge base with FAISS + lightweight BM25.
        Returns an empty list when the KB has no documents yet.
        """
        if self.index is None or not self.chunks:
            return []

        allowed_indexes = set(self._filtered_chunk_indexes(metadata_filter))

        if not allowed_indexes:
            return []

        candidate_k = min(
            len(allowed_indexes),
            max(top_k * 4, top_k, 10),
        )
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
                result_id=index + 1,
                vector_distance=vector_distance,
                bm25_score=bm25_score,
                hybrid_score=hybrid_score,
            )
            for index, (
                chunk_index,
                vector_distance,
                bm25_score,
                hybrid_score,
            ) in enumerate(scored)
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
        """负责 list_documents 的函数职责。"""
        return list_file_records(self.kb_name, user_id=self.user_id)

    def delete_document(self, filename: str) -> dict:
        """
        Delete a document from the KB and rebuild the index.
        Returns a result dict suitable for passing straight back to the client.
        """
        path = os.path.join(self.content_path, filename)

        if not os.path.exists(path):
            return {"error": "file not found"}

        os.remove(path)

        delete_file_record(self.kb_name, filename, user_id=self.user_id)
        delete_file_docs(self.kb_name, filename, user_id=self.user_id)
        self.rebuild_index()

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
        """负责 save_file_record 的函数职责。"""
        self._persist_file_to_db(
            filename,
            file_size,
            status=status,
            error=error,
            content_path=content_path,
            upload_path=upload_path,
        )
