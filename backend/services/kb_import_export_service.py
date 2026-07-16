import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime

from model_config import get_embedding_model_name
from services.kb_service import MiniKBService
from db import (
    create_kb,
    delete_file_docs_by_kb,
    delete_files_by_kb,
    delete_kb_record,
    list_file_records,
    upsert_file_record,
)


DATA_ROOT = "data"
EXPORT_VERSION = 1


def is_safe_kb_name(kb_name):
    return (
        bool(kb_name)
        and not os.path.isabs(kb_name)
        and ".." not in kb_name
        and "/" not in kb_name
        and "\\" not in kb_name
    )


def _kb_path(kb_name):
    return os.path.join(DATA_ROOT, kb_name)


def _build_metadata(kb_name):
    return {
        "version": EXPORT_VERSION,
        "kb_name": kb_name,
        "embedding_model": get_embedding_model_name(),
        "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files": [
            {
                "file_name": file["filename"],
                "file_size": file["size"],
                "docs_count": file["docs_count"],
                "status": file["status"],
                "error": file["error"],
                "chunk_size": file["chunk_size"],
                "chunk_overlap": file["chunk_overlap"],
                "content_path": file["content_path"],
                "upload_path": file["upload_path"],
            }
            for file in list_file_records(kb_name)
        ],
    }


def export_kb(kb_name):
    if not is_safe_kb_name(kb_name):
        return {
            "error": "invalid knowledge base name"
        }

    source_root = _kb_path(kb_name)
    if not os.path.exists(source_root):
        return {
            "error": "knowledge base not found"
        }

    export_file = tempfile.NamedTemporaryFile(
        prefix=f"{kb_name}_",
        suffix="_export.zip",
        delete=False,
    )
    export_file.close()

    metadata = _build_metadata(kb_name)

    with zipfile.ZipFile(export_file.name, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(
            "metadata.json",
            json.dumps(metadata, ensure_ascii=False, indent=2),
        )

        for dirname in ("uploads", "content", "vector_store"):
            directory = os.path.join(source_root, dirname)
            if not os.path.exists(directory):
                continue

            for root, _, files in os.walk(directory):
                for filename in files:
                    path = os.path.join(root, filename)
                    arcname = os.path.relpath(path, source_root)
                    zip_file.write(path, arcname)

    return {
        "path": export_file.name,
        "filename": f"{kb_name}_export.zip",
    }


def _validate_zip_member(member_name):
    normalized = os.path.normpath(member_name)
    return (
        member_name
        and not os.path.isabs(member_name)
        and normalized != ".."
        and not normalized.startswith(f"..{os.sep}")
    )


def _safe_extract(zip_file, destination):
    destination_abs = os.path.abspath(destination)

    for member in zip_file.infolist():
        if not _validate_zip_member(member.filename):
            raise ValueError(f"unsafe zip path: {member.filename}")

        target_path = os.path.abspath(
            os.path.join(destination, member.filename)
        )

        if os.path.commonpath([destination_abs, target_path]) != destination_abs:
            raise ValueError(f"unsafe zip path: {member.filename}")

    zip_file.extractall(destination)


def _copy_kb_directories(extracted_root, target_root):
    os.makedirs(target_root, exist_ok=True)

    for dirname in ("uploads", "content", "vector_store"):
        source = os.path.join(extracted_root, dirname)
        target = os.path.join(target_root, dirname)

        if os.path.exists(target):
            shutil.rmtree(target)

        if os.path.exists(source):
            shutil.copytree(source, target)
        else:
            os.makedirs(target, exist_ok=True)


def _reset_kb_records(kb_name):
    delete_file_docs_by_kb(kb_name)
    delete_files_by_kb(kb_name)
    delete_kb_record(kb_name)


def _restore_file_metadata(kb_name, files):
    for file in files:
        file_name = file.get("file_name")
        if not file_name:
            continue

        content_path = (
            os.path.join(_kb_path(kb_name), "content", file_name)
            if file.get("content_path")
            else None
        )

        upload_path = None
        original_upload_path = file.get("upload_path")
        if original_upload_path:
            upload_path = os.path.join(
                _kb_path(kb_name),
                "uploads",
                os.path.basename(original_upload_path),
            )

        upsert_file_record(
            kb_name,
            file_name,
            file.get("file_size", 0),
            file.get("docs_count", 0),
            status=file.get("status", "indexed"),
            error=file.get("error"),
            chunk_size=file.get("chunk_size", 300),
            chunk_overlap=file.get("chunk_overlap", 50),
            content_path=content_path,
            upload_path=upload_path,
        )


def import_kb(zip_path, override=False):
    if not zip_path.endswith(".zip"):
        return {
            "error": "only .zip files are supported"
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        extract_root = os.path.join(temp_dir, "extract")
        os.makedirs(extract_root, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_file:
            _safe_extract(zip_file, extract_root)

        metadata_path = os.path.join(extract_root, "metadata.json")
        if not os.path.exists(metadata_path):
            return {
                "error": "metadata.json not found"
            }

        with open(metadata_path, "r", encoding="utf-8") as file:
            metadata = json.load(file)

        kb_name = metadata.get("kb_name")
        if not is_safe_kb_name(kb_name):
            return {
                "error": "invalid knowledge base name in metadata"
            }

        target_root = _kb_path(kb_name)

        if os.path.exists(target_root) and not override:
            return {
                "error": f"knowledge base {kb_name} already exists"
            }

        if override and os.path.exists(target_root):
            shutil.rmtree(target_root)

        if override:
            _reset_kb_records(kb_name)

        _copy_kb_directories(extract_root, target_root)

        try:
            create_kb(kb_name)
        except Exception:
            pass

        service = MiniKBService(kb_name)
        service.rebuild_index()
        service.sync_files_to_db()
        _restore_file_metadata(kb_name, metadata.get("files", []))

        return {
            "kb_name": kb_name,
            "files_count": len(metadata.get("files", [])),
            "chunks_count": len(service.chunks),
        }
