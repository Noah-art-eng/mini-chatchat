import os
from datetime import datetime

from sentence_transformers import SentenceTransformer

from rag import load_documents, split_documents, build_faiss_index, search

from db import (
    upsert_file_record,
    delete_file_record,
    list_file_records,
    add_file_doc,
    delete_file_docs
)

ROOT_PATH = "data"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class MiniKBService:
    """
    Service layer that owns all knowledge-base state:
    raw documents, chunk list, FAISS index, and the embedding model.

    Directory layout (ChatChat-style):
        data/{kb_name}/content/       ← parsed .txt files (source of truth)
        data/{kb_name}/uploads/       ← original uploaded files (pdf, etc.)
        data/{kb_name}/vector_store/  ← reserved for future FAISS persistence

    app.py should only call public methods on this class and never
    touch the directory paths or in-memory state directly.
    """

    def __init__(self, kb_name: str = "default"):
        self.kb_name = kb_name
        self.embedding_model_name = EMBEDDING_MODEL

        # Directory paths
        self.root_path = ROOT_PATH
        self.kb_path = os.path.join(ROOT_PATH, kb_name)
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

        # Shared embedding model — loaded once at startup
        self.model = SentenceTransformer(EMBEDDING_MODEL)

        # In-memory state; rebuilt whenever the KB changes
        self.documents: list = []
        self.chunks: list = []
        self.index = None
        self.vectors = None

        self.build_index()

    def _get_file_chunks(self, filename: str) -> list:
        return [
            chunk
            for chunk in self.chunks
            if chunk.get("source") == filename
        ]
    
    def get_chunk_by_id(self, chunk_id: int) -> dict:
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

    def _persist_file_to_db(self, filename: str, file_size: int) -> None:
        """Write knowledge_file + file_doc records for one content file."""
        file_chunks = self._get_file_chunks(filename)

        print(f"[SYNC] {filename} -> {len(file_chunks)} chunks")

        upsert_file_record(
            self.kb_name,
            filename,
            file_size,
            len(file_chunks),
        )

        delete_file_docs(self.kb_name, filename)

        for chunk in file_chunks:
            add_file_doc(
                self.kb_name,
                filename,
                chunk["chunk_id"],
            )

    def sync_files_to_db(self):
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
        self.chunks = split_documents(self.documents)
        return self.chunks

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rebuild_index(self) -> None:
        """Full re-index after any document change (upload / delete)."""
        self.build_index()

    def search_docs(
        self,
        query: str,
        top_k: int = 3,
        score_threshold: float = 0.8,
    ) -> list:
        """
        Vector-search the knowledge base.
        Returns an empty list when the KB has no documents yet.
        """
        if self.index is None or not self.chunks:
            return []

        return search(
            query,
            self.index,
            self.chunks,
            self.model,
            top_k,
            score_threshold,
        )

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
        return list_file_records(self.kb_name)

    def delete_document(self, filename: str) -> dict:
        """
        Delete a document from the KB and rebuild the index.
        Returns a result dict suitable for passing straight back to the client.
        """
        path = os.path.join(self.content_path, filename)

        if not os.path.exists(path):
            return {"error": "file not found"}

        os.remove(path)

        delete_file_record(self.kb_name, filename)
        delete_file_docs(self.kb_name, filename)
        self.rebuild_index()

        return {"message": f"{filename} deleted"}

    def save_file_record(self, filename, file_size):
        self._persist_file_to_db(filename, file_size)