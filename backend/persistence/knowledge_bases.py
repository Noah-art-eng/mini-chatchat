"""Knowledge Base、文件元数据和 chunk 映射的 SQLite 持久化实现。"""

from datetime import datetime


def create_default_kb(get_connection, resolve_user_id, user_id=None):
    """为目标用户创建默认知识库记录。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO knowledge_base (
            kb_name,
            embed_model,
            create_time,
            user_id
        )
        VALUES (?, ?, ?, ?)
    """, (
        "default",
        "all-MiniLM-L6-v2",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        resolved_user_id,
    ))

    conn.commit()
    conn.close()


def list_kbs(get_connection, resolve_user_id, user_id=None):
    """列出目标用户的知识库元数据。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, kb_name, embed_model, create_time
        FROM knowledge_base
        WHERE user_id = ?
        ORDER BY id
    """, (
        resolved_user_id,
    ))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "kb_name": row[1],
            "embed_model": row[2],
            "create_time": row[3]
        }
        for row in rows
    ]


def get_kb_record(get_connection, resolve_user_id, kb_name, user_id=None):
    """读取目标用户的指定知识库记录。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, kb_name, embed_model, create_time, user_id
        FROM knowledge_base
        WHERE kb_name = ? AND user_id = ?
    """, (
        kb_name,
        resolved_user_id,
    ))

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "kb_name": row[1],
        "embed_model": row[2],
        "create_time": row[3],
        "user_id": row[4],
    }


def user_owns_kb(get_connection, resolve_user_id, kb_name, user_id=None):
    """判断目标用户是否拥有指定知识库。"""
    return get_kb_record(
        get_connection,
        resolve_user_id,
        kb_name,
        user_id=user_id,
    ) is not None


def create_kb(get_connection, resolve_user_id, kb_name, user_id=None):
    """创建目标用户的知识库元数据。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO knowledge_base (
            kb_name,
            embed_model,
            create_time,
            user_id
        )
        VALUES (?, ?, ?, ?)
    """, (
        kb_name,
        "all-MiniLM-L6-v2",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        resolved_user_id,
    ))

    conn.commit()
    conn.close()


def upsert_file_record(
    get_connection,
    resolve_user_id,
    kb_name,
    file_name,
    file_size,
    docs_count,
    status="indexed",
    error=None,
    chunk_size=300,
    chunk_overlap=50,
    content_path=None,
    upload_path=None,
    user_id=None,
):
    """新增或替换知识库文件元数据。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO knowledge_file (
            kb_name,
            file_name,
            file_size,
            docs_count,
            update_time,
            status,
            error,
            chunk_size,
            chunk_overlap,
            content_path,
            upload_path,
            user_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        kb_name,
        file_name,
        file_size,
        docs_count,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        status,
        error,
        chunk_size,
        chunk_overlap,
        content_path,
        upload_path,
        resolved_user_id,
    ))

    conn.commit()
    conn.close()


def update_file_status(
    get_connection,
    resolve_user_id,
    kb_name,
    file_name,
    status,
    error=None,
    user_id=None,
):
    """更新知识库文件的索引状态。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE knowledge_file
        SET status = ?,
            error = ?,
            update_time = ?
        WHERE kb_name = ? AND file_name = ? AND user_id = ?
    """, (
        status,
        error,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        kb_name,
        file_name,
        resolved_user_id,
    ))

    conn.commit()
    conn.close()


def delete_file_record(
    get_connection,
    resolve_user_id,
    kb_name,
    file_name,
    user_id=None,
):
    """删除目标用户的知识库文件元数据。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM knowledge_file
        WHERE kb_name = ? AND file_name = ? AND user_id = ?
    """, (
        kb_name,
        file_name,
        resolved_user_id,
    ))

    conn.commit()
    conn.close()


def list_file_records(get_connection, resolve_user_id, kb_name, user_id=None):
    """列出目标用户知识库中的文件元数据。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            file_name,
            file_size,
            docs_count,
            update_time,
            status,
            error,
            chunk_size,
            chunk_overlap,
            content_path,
            upload_path
        FROM knowledge_file
        WHERE kb_name = ? AND user_id = ?
    """, (
        kb_name,
        resolved_user_id,
    ))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "filename": row[0],
            "size": row[1],
            "docs_count": row[2],
            "time": row[3],
            "status": row[4],
            "error": row[5],
            "chunk_size": row[6],
            "chunk_overlap": row[7],
            "content_path": row[8],
            "upload_path": row[9],
        }
        for row in rows
    ]


def add_file_doc(
    get_connection,
    resolve_user_id,
    kb_name,
    file_name,
    chunk_id,
    user_id=None,
):
    """新增文件与 chunk 的映射。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO file_doc (
            kb_name,
            file_name,
            chunk_id,
            user_id
        )
        VALUES (?, ?, ?, ?)
    """, (
        kb_name,
        file_name,
        int(chunk_id),
        resolved_user_id,
    ))

    conn.commit()
    conn.close()
    print(f"INSERT FILE_DOC -> {file_name} : {chunk_id}")


def delete_file_docs(
    get_connection,
    resolve_user_id,
    kb_name,
    file_name,
    user_id=None,
):
    """删除指定文件的全部 chunk 映射。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM file_doc
        WHERE kb_name = ? AND file_name = ? AND user_id = ?
    """, (
        kb_name,
        file_name,
        resolved_user_id,
    ))

    conn.commit()
    conn.close()


def list_file_docs(
    get_connection,
    resolve_user_id,
    kb_name,
    file_name,
    user_id=None,
):
    """按 chunk_id 顺序读取指定文件的映射。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT chunk_id
        FROM file_doc
        WHERE kb_name = ? AND file_name = ? AND user_id = ?
        ORDER BY chunk_id
    """, (
        kb_name,
        file_name,
        resolved_user_id,
    ))

    rows = cursor.fetchall()
    conn.close()

    return [
        {"chunk_id": row[0]}
        for row in rows
    ]


def sync_kb_file_mappings(
    get_connection,
    resolve_user_id,
    kb_name,
    files,
    user_id=None,
):
    """在一个事务内重建当前 KB 的 file_doc，并同步每个文件的 chunk 数。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                file_name,
                status,
                error,
                chunk_size,
                chunk_overlap,
                content_path,
                upload_path
            FROM knowledge_file
            WHERE kb_name = ? AND user_id = ?
            """,
            (kb_name, resolved_user_id),
        )
        existing = {
            row[0]: {
                "status": row[1],
                "error": row[2],
                "chunk_size": row[3],
                "chunk_overlap": row[4],
                "content_path": row[5],
                "upload_path": row[6],
            }
            for row in cursor.fetchall()
        }

        cursor.execute(
            "DELETE FROM file_doc WHERE kb_name = ? AND user_id = ?",
            (kb_name, resolved_user_id),
        )

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for file in files:
            filename = file["filename"]
            previous = existing.get(filename, {})
            override = file.get("metadata", {})
            values = {
                "status": override.get("status", previous.get("status", "indexed")),
                "error": override.get("error", previous.get("error")),
                "chunk_size": override.get(
                    "chunk_size",
                    previous.get("chunk_size", 300),
                ),
                "chunk_overlap": override.get(
                    "chunk_overlap",
                    previous.get("chunk_overlap", 50),
                ),
                "content_path": override.get(
                    "content_path",
                    previous.get("content_path"),
                ),
                "upload_path": override.get(
                    "upload_path",
                    previous.get("upload_path"),
                ),
            }
            cursor.execute(
                """
                INSERT INTO knowledge_file (
                    kb_name, file_name, file_size, docs_count, update_time,
                    status, error, chunk_size, chunk_overlap,
                    content_path, upload_path, user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, kb_name, file_name) DO UPDATE SET
                    file_size = excluded.file_size,
                    docs_count = excluded.docs_count,
                    update_time = excluded.update_time,
                    status = excluded.status,
                    error = excluded.error,
                    chunk_size = excluded.chunk_size,
                    chunk_overlap = excluded.chunk_overlap,
                    content_path = excluded.content_path,
                    upload_path = excluded.upload_path
                """,
                (
                    kb_name,
                    filename,
                    file["size"],
                    len(file["chunk_ids"]),
                    now,
                    values["status"],
                    values["error"],
                    values["chunk_size"],
                    values["chunk_overlap"],
                    values["content_path"],
                    values["upload_path"],
                    resolved_user_id,
                ),
            )
            for chunk_id in file["chunk_ids"]:
                cursor.execute(
                    """
                    INSERT INTO file_doc (kb_name, file_name, chunk_id, user_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (kb_name, filename, int(chunk_id), resolved_user_id),
                )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_file_docs_by_kb(
    get_connection,
    resolve_user_id,
    kb_name,
    user_id=None,
):
    """删除目标知识库的全部 chunk 映射。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM file_doc
        WHERE kb_name = ? AND user_id = ?
    """, (
        kb_name,
        resolved_user_id,
    ))

    conn.commit()
    conn.close()


def delete_files_by_kb(
    get_connection,
    resolve_user_id,
    kb_name,
    user_id=None,
):
    """删除目标知识库的全部文件元数据。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM knowledge_file
        WHERE kb_name = ? AND user_id = ?
    """, (
        kb_name,
        resolved_user_id,
    ))

    conn.commit()
    conn.close()


def delete_kb_record(
    get_connection,
    resolve_user_id,
    kb_name,
    user_id=None,
):
    """删除目标用户的知识库元数据。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM knowledge_base
        WHERE kb_name = ? AND user_id = ?
    """, (
        kb_name,
        resolved_user_id,
    ))

    conn.commit()
    conn.close()
