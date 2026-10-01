import os
import sqlite3
from datetime import datetime
from persistence.auth import (
    cleanup_expired_auth_sessions as _cleanup_expired_auth_sessions,
    create_auth_session as _create_auth_session,
    create_email_user as _create_email_user,
    create_user as _create_user,
    delete_oauth_account_for_user as _delete_oauth_account_for_user,
    get_auth_session as _get_auth_session,
    get_oauth_account as _get_oauth_account,
    get_oauth_account_for_user as _get_oauth_account_for_user,
    get_user_auth_by_email as _get_user_auth_by_email,
    get_user_by_email as _get_user_by_email,
    get_user_by_id as _get_user_by_id,
    get_user_password_hash as _get_user_password_hash,
    get_user_preferences as _get_user_preferences,
    list_auth_sessions_by_user as _list_auth_sessions_by_user,
    list_oauth_accounts_for_user as _list_oauth_accounts_for_user,
    public_oauth_account,
    public_user_dict,
    revoke_auth_session as _revoke_auth_session,
    revoke_auth_session_for_user as _revoke_auth_session_for_user,
    revoke_other_auth_sessions as _revoke_other_auth_sessions,
    revoke_user_auth_sessions as _revoke_user_auth_sessions,
    row_to_auth_session,
    row_to_oauth_account,
    row_to_user,
    set_user_active as _set_user_active,
    update_auth_session_refresh as _update_auth_session_refresh,
    update_user_account as _update_user_account,
    upsert_oauth_account as _upsert_oauth_account,
    upsert_user_preferences as _upsert_user_preferences,
    user_login_method_count as _user_login_method_count,
)
from persistence.connection import connection_scope, open_connection
from persistence.conversations import (
    create_conversation as _create_conversation,
    decode_metadata,
    delete_conversation as _delete_conversation,
    encode_metadata,
    get_conversation as _get_conversation,
    get_conversation_messages as _get_conversation_messages,
    list_conversations as _list_conversations,
    save_message as _save_message,
    update_conversation_title as _update_conversation_title,
    update_message_feedback as _update_message_feedback,
)
from persistence.schema import (
    ensure_user_scoped_unique_constraints,
    has_unique_index,
    init_db as initialize_schema,
)
from user_scope import DEMO_USER_EMAIL

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("MINI_CHATCHAT_DB_PATH", os.path.join(BASE_DIR, "mini.db"))
_DEMO_USER_ID_CACHE = None


def get_connection():
    """通过当前 facade 的 DB_PATH 创建连接，保留测试和部署时的动态配置。"""
    return open_connection(DB_PATH)


@connection_scope
def init_db():
    """使用当前连接配置初始化 schema，并执行原有兼容迁移。"""
    return initialize_schema(get_connection, DEMO_USER_EMAIL)


@connection_scope
def get_demo_user_id():
    """负责 get_demo_user_id 的函数职责。"""
    global _DEMO_USER_ID_CACHE

    if _DEMO_USER_ID_CACHE is not None:
        return _DEMO_USER_ID_CACHE

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT OR IGNORE INTO users (
            email,
            display_name,
            avatar_url,
            auth_provider,
            password_hash,
            created_at,
            updated_at,
            is_guest,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        DEMO_USER_EMAIL,
        "Demo User",
        None,
        "demo",
        None,
        now,
        now,
        0,
        1,
    ))

    cursor.execute("""
        SELECT id
        FROM users
        WHERE email = ?
    """, (
        DEMO_USER_EMAIL,
    ))

    row = cursor.fetchone()
    conn.commit()
    conn.close()

    _DEMO_USER_ID_CACHE = row[0]
    return _DEMO_USER_ID_CACHE


def resolve_user_id(user_id=None):
    """负责 resolve_user_id 的函数职责。"""
    return user_id if user_id is not None else get_demo_user_id()


@connection_scope
def create_default_kb(user_id=None):
    """负责 create_default_kb 的函数职责。"""
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


@connection_scope
def get_user_by_id(user_id):
    """通过兼容 facade 按 ID 查询用户。"""
    return _get_user_by_id(get_connection, user_id)


@connection_scope
def get_user_by_email(email):
    """通过兼容 facade 按邮箱查询用户。"""
    return _get_user_by_email(get_connection, email)


@connection_scope
def get_user_auth_by_email(email):
    """通过兼容 facade 读取邮箱登录所需的用户记录。"""
    return _get_user_auth_by_email(get_connection, email)


@connection_scope
def create_user(
    email=None,
    display_name=None,
    avatar_url=None,
    auth_provider="email",
    password_hash=None,
    is_guest=False,
    is_active=True,
):
    """通过兼容 facade 创建用户及默认偏好。"""
    return _create_user(
        get_connection,
        email,
        display_name,
        avatar_url,
        auth_provider,
        password_hash,
        is_guest,
        is_active,
    )


@connection_scope
def get_user_password_hash(user_id):
    """通过兼容 facade 读取用户密码摘要。"""
    return _get_user_password_hash(get_connection, user_id)


@connection_scope
def create_email_user(email, password_hash, display_name=None):
    """通过兼容 facade 创建邮箱用户。"""
    return _create_email_user(
        get_connection,
        email,
        password_hash,
        display_name,
    )


@connection_scope
def set_user_active(user_id, is_active):
    """通过兼容 facade 更新用户启用状态。"""
    return _set_user_active(get_connection, user_id, is_active)


@connection_scope
def update_user_account(user_id, display_name):
    """通过兼容 facade 更新用户资料。"""
    return _update_user_account(get_connection, user_id, display_name)


@connection_scope
def get_oauth_account(provider, provider_user_id):
    """通过兼容 facade 查询 OAuth 身份。"""
    return _get_oauth_account(get_connection, provider, provider_user_id)


@connection_scope
def get_oauth_account_for_user(user_id, provider):
    """通过兼容 facade 查询用户关联的 OAuth 身份。"""
    return _get_oauth_account_for_user(get_connection, user_id, provider)


@connection_scope
def list_oauth_accounts_for_user(user_id):
    """通过兼容 facade 列出用户关联的 OAuth 身份。"""
    return _list_oauth_accounts_for_user(get_connection, user_id)


@connection_scope
def upsert_oauth_account(
    user_id,
    provider,
    provider_user_id,
    provider_email=None,
    provider_display_name=None,
    provider_avatar=None,
):
    """通过兼容 facade 新增或更新 OAuth 身份。"""
    return _upsert_oauth_account(
        get_connection,
        user_id,
        provider,
        provider_user_id,
        provider_email,
        provider_display_name,
        provider_avatar,
    )


@connection_scope
def delete_oauth_account_for_user(user_id, provider):
    """通过兼容 facade 删除用户关联的 OAuth 身份。"""
    return _delete_oauth_account_for_user(get_connection, user_id, provider)


@connection_scope
def user_login_method_count(user_id):
    """通过兼容 facade 统计用户仍可用的登录方式。"""
    return _user_login_method_count(get_connection, user_id)


@connection_scope
def create_auth_session(
    session_id,
    user_id,
    refresh_token_hash,
    expires_at,
    user_agent=None,
    ip_address=None,
):
    """通过兼容 facade 创建认证会话。"""
    return _create_auth_session(
        get_connection,
        session_id,
        user_id,
        refresh_token_hash,
        expires_at,
        user_agent,
        ip_address,
    )


@connection_scope
def get_auth_session(session_id):
    """通过兼容 facade 查询认证会话。"""
    return _get_auth_session(get_connection, session_id)


@connection_scope
def list_auth_sessions_by_user(user_id):
    """通过兼容 facade 列出用户的认证会话。"""
    return _list_auth_sessions_by_user(get_connection, user_id)


@connection_scope
def update_auth_session_refresh(session_id, refresh_token_hash, expires_at):
    """通过兼容 facade 轮换认证会话的 refresh token。"""
    return _update_auth_session_refresh(
        get_connection,
        session_id,
        refresh_token_hash,
        expires_at,
    )


@connection_scope
def revoke_auth_session(session_id):
    """通过兼容 facade 撤销认证会话。"""
    return _revoke_auth_session(get_connection, session_id)


@connection_scope
def revoke_auth_session_for_user(user_id, session_id):
    """通过兼容 facade 撤销用户自己的指定会话。"""
    return _revoke_auth_session_for_user(get_connection, user_id, session_id)


@connection_scope
def revoke_other_auth_sessions(user_id, current_session_id):
    """通过兼容 facade 撤销用户当前会话之外的会话。"""
    return _revoke_other_auth_sessions(
        get_connection,
        user_id,
        current_session_id,
    )


@connection_scope
def revoke_user_auth_sessions(user_id):
    """通过兼容 facade 撤销用户的全部会话。"""
    return _revoke_user_auth_sessions(get_connection, user_id)


@connection_scope
def cleanup_expired_auth_sessions():
    """通过兼容 facade 标记已过期的认证会话。"""
    return _cleanup_expired_auth_sessions(get_connection)


@connection_scope
def get_user_preferences(user_id):
    """通过兼容 facade 读取用户偏好。"""
    return _get_user_preferences(get_connection, user_id)


@connection_scope
def upsert_user_preferences(
    user_id,
    language=None,
    developer_mode=False,
    onboarding_completed=False,
    theme="light",
    preferred_model=None,
):
    """通过兼容 facade 新增或更新用户偏好。"""
    return _upsert_user_preferences(
        get_connection,
        user_id,
        language,
        developer_mode,
        onboarding_completed,
        theme,
        preferred_model,
    )


@connection_scope
def list_kbs(user_id=None):
    """负责 list_kbs 的函数职责。"""
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

@connection_scope
def get_kb_record(kb_name, user_id=None):
    """负责 get_kb_record 的函数职责。"""
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


def user_owns_kb(kb_name, user_id=None):
    """负责 user_owns_kb 的函数职责。"""
    return get_kb_record(kb_name, user_id=user_id) is not None


@connection_scope
def create_kb(kb_name, user_id=None):
    """负责 create_kb 的函数职责。"""
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


@connection_scope
def create_conversation(title=None, user_id=None):
    """通过兼容 facade 创建当前用户的会话。"""
    return _create_conversation(get_connection, resolve_user_id, title, user_id)


@connection_scope
def list_conversations(user_id=None):
    """通过兼容 facade 返回当前用户的会话列表。"""
    return _list_conversations(get_connection, resolve_user_id, user_id)


@connection_scope
def get_conversation(conversation_id, user_id=None):
    """通过兼容 facade 读取当前用户的指定会话。"""
    return _get_conversation(
        get_connection,
        resolve_user_id,
        conversation_id,
        user_id,
    )


@connection_scope
def update_conversation_title(conversation_id, title, user_id=None):
    """通过兼容 facade 更新当前用户的会话标题。"""
    return _update_conversation_title(
        get_connection,
        resolve_user_id,
        conversation_id,
        title,
        user_id,
    )


@connection_scope
def delete_conversation(conversation_id, user_id=None):
    """通过兼容 facade 删除当前用户的会话及其消息。"""
    return _delete_conversation(
        get_connection,
        resolve_user_id,
        conversation_id,
        user_id,
    )


@connection_scope
def save_message(conversation_id, role, content, metadata=None, user_id=None):
    """通过兼容 facade 保存消息并更新会话时间。"""
    return _save_message(
        get_connection,
        resolve_user_id,
        conversation_id,
        role,
        content,
        metadata,
        user_id,
    )


@connection_scope
def get_conversation_messages(conversation_id, user_id=None):
    """通过兼容 facade 读取当前用户的会话消息。"""
    return _get_conversation_messages(
        get_connection,
        resolve_user_id,
        conversation_id,
        user_id,
    )


@connection_scope
def update_message_feedback(message_id, score, reason=None, user_id=None):
    """通过兼容 facade 更新当前用户的消息反馈。"""
    return _update_message_feedback(
        get_connection,
        resolve_user_id,
        message_id,
        score,
        reason,
        user_id,
    )


@connection_scope
def upsert_file_record(
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
    """负责 upsert_file_record 的函数职责。"""
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


@connection_scope
def update_file_status(kb_name, file_name, status, error=None, user_id=None):
    """负责 update_file_status 的函数职责。"""
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


@connection_scope
def delete_file_record(kb_name, file_name, user_id=None):
    """负责 delete_file_record 的函数职责。"""
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

@connection_scope
def list_file_records(kb_name, user_id=None):
    """负责 list_file_records 的函数职责。"""
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

@connection_scope
def add_file_doc(kb_name, file_name, chunk_id, user_id=None):
    """负责 add_file_doc 的函数职责。"""
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

@connection_scope
def delete_file_docs(kb_name, file_name, user_id=None):
    """负责 delete_file_docs 的函数职责。"""
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

@connection_scope
def list_file_docs(kb_name, file_name, user_id=None):
    """负责 list_file_docs 的函数职责。"""
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


@connection_scope
def sync_kb_file_mappings(kb_name, files, user_id=None):
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

@connection_scope
def delete_file_docs_by_kb(kb_name, user_id=None):
    """负责 delete_file_docs_by_kb 的函数职责。"""
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


@connection_scope
def delete_files_by_kb(kb_name, user_id=None):
    """负责 delete_files_by_kb 的函数职责。"""
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


@connection_scope
def delete_kb_record(kb_name, user_id=None):
    """负责 delete_kb_record 的函数职责。"""
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
