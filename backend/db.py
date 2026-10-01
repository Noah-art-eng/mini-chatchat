import os
import sqlite3
from datetime import datetime
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


def row_to_user(row):
    """负责 row_to_user 的函数职责。"""
    if row is None:
        return None

    return {
        "id": row[0],
        "email": row[1],
        "display_name": row[2],
        "avatar_url": row[3],
        "auth_provider": row[4],
        "created_at": row[5],
        "updated_at": row[6],
        "is_guest": bool(row[7]),
        "is_active": bool(row[8]),
    }


def public_user_dict(user):
    """负责 public_user_dict 的函数职责。"""
    if user is None:
        return None

    return {
        "id": user["id"],
        "email": user.get("email"),
        "display_name": user.get("display_name"),
        "avatar_url": user.get("avatar_url"),
        "auth_provider": user.get("auth_provider"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
        "is_guest": bool(user.get("is_guest")),
        "is_active": bool(user.get("is_active")),
    }


@connection_scope
def get_user_by_id(user_id):
    """负责 get_user_by_id 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            email,
            display_name,
            avatar_url,
            auth_provider,
            created_at,
            updated_at,
            is_guest,
            is_active
        FROM users
        WHERE id = ?
    """, (
        user_id,
    ))

    user = row_to_user(cursor.fetchone())
    conn.close()

    return user


@connection_scope
def get_user_by_email(email):
    """负责 get_user_by_email 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            email,
            display_name,
            avatar_url,
            auth_provider,
            created_at,
            updated_at,
            is_guest,
            is_active
        FROM users
        WHERE email = ?
    """, (
        email,
    ))

    user = row_to_user(cursor.fetchone())
    conn.close()

    return user


@connection_scope
def get_user_auth_by_email(email):
    """负责 get_user_auth_by_email 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            email,
            display_name,
            avatar_url,
            auth_provider,
            created_at,
            updated_at,
            is_guest,
            is_active,
            password_hash
        FROM users
        WHERE lower(email) = lower(?)
    """, (
        email,
    ))

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    user = row_to_user(row[:9])
    user["password_hash"] = row[9]
    return user


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
    """负责 create_user 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO users (
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
        email,
        display_name,
        avatar_url,
        auth_provider,
        password_hash,
        now,
        now,
        1 if is_guest else 0,
        1 if is_active else 0,
    ))

    user_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO user_preferences (
            user_id,
            language,
            developer_mode,
            onboarding_completed,
            theme,
            preferred_model,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        None,
        0,
        0,
        "light",
        None,
        now,
        now,
    ))

    conn.commit()
    conn.close()

    return get_user_by_id(user_id)


@connection_scope
def get_user_password_hash(user_id):
    """负责 get_user_password_hash 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT password_hash
        FROM users
        WHERE id = ?
    """, (
        user_id,
    ))

    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def create_email_user(email, password_hash, display_name=None):
    """负责 create_email_user 的函数职责。"""
    return create_user(
        email=email,
        display_name=display_name or email,
        auth_provider="email",
        password_hash=password_hash,
        is_guest=False,
        is_active=True,
    )


@connection_scope
def set_user_active(user_id, is_active):
    """负责 set_user_active 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE users
        SET is_active = ?,
            updated_at = ?
        WHERE id = ?
    """, (
        1 if is_active else 0,
        now,
        user_id,
    ))

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return updated > 0


@connection_scope
def update_user_account(user_id, display_name):
    """负责 update_user_account 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE users
        SET display_name = ?,
            updated_at = ?
        WHERE id = ?
          AND is_active = 1
    """, (
        display_name,
        now,
        user_id,
    ))

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return get_user_by_id(user_id) if updated else None


def row_to_oauth_account(row):
    """负责 row_to_oauth_account 的函数职责。"""
    if row is None:
        return None

    return {
        "id": row[0],
        "user_id": row[1],
        "provider": row[2],
        "provider_user_id": row[3],
        "provider_email": row[4],
        "provider_display_name": row[5],
        "provider_avatar": row[6],
        "created_at": row[7],
        "updated_at": row[8],
    }


def public_oauth_account(account):
    """负责 public_oauth_account 的函数职责。"""
    if account is None:
        return None

    return {
        "provider": account["provider"],
        "provider_email": account.get("provider_email"),
        "provider_display_name": account.get("provider_display_name"),
        "provider_avatar": account.get("provider_avatar"),
        "created_at": account.get("created_at"),
        "updated_at": account.get("updated_at"),
    }


@connection_scope
def get_oauth_account(provider, provider_user_id):
    """负责 get_oauth_account 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            user_id,
            provider,
            provider_user_id,
            provider_email,
            provider_display_name,
            provider_avatar,
            created_at,
            updated_at
        FROM oauth_accounts
        WHERE provider = ?
          AND provider_user_id = ?
    """, (
        provider,
        provider_user_id,
    ))

    account = row_to_oauth_account(cursor.fetchone())
    conn.close()
    return account


@connection_scope
def get_oauth_account_for_user(user_id, provider):
    """负责 get_oauth_account_for_user 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            user_id,
            provider,
            provider_user_id,
            provider_email,
            provider_display_name,
            provider_avatar,
            created_at,
            updated_at
        FROM oauth_accounts
        WHERE user_id = ?
          AND provider = ?
    """, (
        user_id,
        provider,
    ))

    account = row_to_oauth_account(cursor.fetchone())
    conn.close()
    return account


@connection_scope
def list_oauth_accounts_for_user(user_id):
    """负责 list_oauth_accounts_for_user 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            user_id,
            provider,
            provider_user_id,
            provider_email,
            provider_display_name,
            provider_avatar,
            created_at,
            updated_at
        FROM oauth_accounts
        WHERE user_id = ?
        ORDER BY provider ASC
    """, (
        user_id,
    ))

    accounts = [
        row_to_oauth_account(row)
        for row in cursor.fetchall()
    ]
    conn.close()
    return accounts


@connection_scope
def upsert_oauth_account(
    user_id,
    provider,
    provider_user_id,
    provider_email=None,
    provider_display_name=None,
    provider_avatar=None,
):
    """负责 upsert_oauth_account 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO oauth_accounts (
            user_id,
            provider,
            provider_user_id,
            provider_email,
            provider_display_name,
            provider_avatar,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(provider, provider_user_id)
        DO UPDATE SET
            provider_email = excluded.provider_email,
            provider_display_name = excluded.provider_display_name,
            provider_avatar = excluded.provider_avatar,
            updated_at = excluded.updated_at
    """, (
        user_id,
        provider,
        provider_user_id,
        provider_email,
        provider_display_name,
        provider_avatar,
        now,
        now,
    ))

    conn.commit()
    conn.close()
    return get_oauth_account(provider, provider_user_id)


@connection_scope
def delete_oauth_account_for_user(user_id, provider):
    """负责 delete_oauth_account_for_user 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM oauth_accounts
        WHERE user_id = ?
          AND provider = ?
    """, (
        user_id,
        provider,
    ))

    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted > 0


def user_login_method_count(user_id):
    """负责 user_login_method_count 的函数职责。"""
    password_hash = get_user_password_hash(user_id)
    oauth_count = len(list_oauth_accounts_for_user(user_id))
    return (1 if password_hash else 0) + oauth_count


@connection_scope
def create_auth_session(
    session_id,
    user_id,
    refresh_token_hash,
    expires_at,
    user_agent=None,
    ip_address=None,
):
    """负责 create_auth_session 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO auth_sessions (
            session_id,
            user_id,
            refresh_token_hash,
            created_at,
            updated_at,
            expires_at,
            revoked_at,
            last_used_at,
            user_agent,
            ip_address,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, 1)
    """, (
        session_id,
        user_id,
        refresh_token_hash,
        now,
        now,
        expires_at,
        user_agent,
        ip_address,
    ))

    conn.commit()
    conn.close()

    return get_auth_session(session_id)


def row_to_auth_session(row):
    """负责 row_to_auth_session 的函数职责。"""
    if row is None:
        return None

    return {
        "id": row[0],
        "session_id": row[1],
        "user_id": row[2],
        "refresh_token_hash": row[3],
        "created_at": row[4],
        "updated_at": row[5],
        "expires_at": row[6],
        "revoked_at": row[7],
        "last_used_at": row[8],
        "user_agent": row[9],
        "ip_address": row[10],
        "is_active": bool(row[11]),
    }


@connection_scope
def get_auth_session(session_id):
    """负责 get_auth_session 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            session_id,
            user_id,
            refresh_token_hash,
            created_at,
            updated_at,
            expires_at,
            revoked_at,
            last_used_at,
            user_agent,
            ip_address,
            is_active
        FROM auth_sessions
        WHERE session_id = ?
    """, (
        session_id,
    ))

    session = row_to_auth_session(cursor.fetchone())
    conn.close()
    return session


@connection_scope
def list_auth_sessions_by_user(user_id):
    """负责 list_auth_sessions_by_user 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            session_id,
            user_id,
            refresh_token_hash,
            created_at,
            updated_at,
            expires_at,
            revoked_at,
            last_used_at,
            user_agent,
            ip_address,
            is_active
        FROM auth_sessions
        WHERE user_id = ?
        ORDER BY
            CASE WHEN revoked_at IS NULL AND is_active = 1 THEN 0 ELSE 1 END,
            COALESCE(last_used_at, updated_at, created_at) DESC
    """, (
        user_id,
    ))

    sessions = [
        row_to_auth_session(row)
        for row in cursor.fetchall()
    ]
    conn.close()
    return sessions


@connection_scope
def update_auth_session_refresh(
    session_id,
    refresh_token_hash,
    expires_at,
):
    """负责 update_auth_session_refresh 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE auth_sessions
        SET refresh_token_hash = ?,
            updated_at = ?,
            last_used_at = ?,
            expires_at = ?
        WHERE session_id = ?
          AND revoked_at IS NULL
          AND is_active = 1
    """, (
        refresh_token_hash,
        now,
        now,
        expires_at,
        session_id,
    ))

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return updated > 0


@connection_scope
def revoke_auth_session(session_id):
    """负责 revoke_auth_session 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE auth_sessions
        SET revoked_at = ?,
            updated_at = ?,
            is_active = 0
        WHERE session_id = ?
    """, (
        now,
        now,
        session_id,
    ))

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return updated > 0


@connection_scope
def revoke_auth_session_for_user(user_id, session_id):
    """负责 revoke_auth_session_for_user 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE auth_sessions
        SET revoked_at = ?,
            updated_at = ?,
            is_active = 0
        WHERE user_id = ?
          AND session_id = ?
          AND revoked_at IS NULL
    """, (
        now,
        now,
        user_id,
        session_id,
    ))

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return updated > 0


@connection_scope
def revoke_other_auth_sessions(user_id, current_session_id):
    """负责 revoke_other_auth_sessions 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE auth_sessions
        SET revoked_at = ?,
            updated_at = ?,
            is_active = 0
        WHERE user_id = ?
          AND session_id != ?
          AND revoked_at IS NULL
    """, (
        now,
        now,
        user_id,
        current_session_id,
    ))

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return updated


@connection_scope
def revoke_user_auth_sessions(user_id):
    """负责 revoke_user_auth_sessions 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE auth_sessions
        SET revoked_at = ?,
            updated_at = ?,
            is_active = 0
        WHERE user_id = ?
          AND revoked_at IS NULL
    """, (
        now,
        now,
        user_id,
    ))

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return updated


@connection_scope
def cleanup_expired_auth_sessions():
    """负责 cleanup_expired_auth_sessions 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE auth_sessions
        SET is_active = 0,
            revoked_at = COALESCE(revoked_at, ?),
            updated_at = ?
        WHERE expires_at < ?
          AND is_active = 1
    """, (
        now,
        now,
        now,
    ))

    updated = cursor.rowcount
    conn.commit()
    conn.close()
    return updated


@connection_scope
def get_user_preferences(user_id):
    """负责 get_user_preferences 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            user_id,
            language,
            developer_mode,
            onboarding_completed,
            theme,
            preferred_model,
            created_at,
            updated_at
        FROM user_preferences
        WHERE user_id = ?
    """, (
        user_id,
    ))

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "user_id": row[0],
        "language": row[1],
        "developer_mode": bool(row[2]),
        "onboarding_completed": bool(row[3]),
        "theme": row[4],
        "preferred_model": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }


@connection_scope
def upsert_user_preferences(
    user_id,
    language=None,
    developer_mode=False,
    onboarding_completed=False,
    theme="light",
    preferred_model=None,
):
    """负责 upsert_user_preferences 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO user_preferences (
            user_id,
            language,
            developer_mode,
            onboarding_completed,
            theme,
            preferred_model,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            language = excluded.language,
            developer_mode = excluded.developer_mode,
            onboarding_completed = excluded.onboarding_completed,
            theme = excluded.theme,
            preferred_model = excluded.preferred_model,
            updated_at = excluded.updated_at
    """, (
        user_id,
        language,
        1 if developer_mode else 0,
        1 if onboarding_completed else 0,
        theme,
        preferred_model,
        now,
        now,
    ))

    conn.commit()
    conn.close()

    return get_user_preferences(user_id)


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
