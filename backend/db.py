import json
import os
import sqlite3
from datetime import datetime
from user_scope import DEMO_USER_EMAIL

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("MINI_CHATCHAT_DB_PATH", os.path.join(BASE_DIR, "mini.db"))
_DEMO_USER_ID_CACHE = None


def get_connection():
    """负责 get_connection 的函数职责。"""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def has_unique_index(cursor, table_name, expected_columns):
    """负责 has_unique_index 的函数职责。"""
    cursor.execute(f"PRAGMA index_list({table_name})")
    indexes = cursor.fetchall()

    for index in indexes:
        index_name = index[1]
        is_unique = bool(index[2])

        if not is_unique:
            continue

        cursor.execute(f"PRAGMA index_info({index_name})")
        columns = [row[2] for row in cursor.fetchall()]

        if columns == expected_columns:
            return True

    return False


def ensure_user_scoped_unique_constraints(cursor, demo_user_id):
    """负责 ensure_user_scoped_unique_constraints 的函数职责。"""
    if not has_unique_index(cursor, "knowledge_base", ["user_id", "kb_name"]):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kb_name TEXT NOT NULL,
                embed_model TEXT NOT NULL,
                create_time TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                UNIQUE(user_id, kb_name)
            )
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO knowledge_base_new (
                id,
                kb_name,
                embed_model,
                create_time,
                user_id
            )
            SELECT
                id,
                kb_name,
                embed_model,
                create_time,
                COALESCE(user_id, ?)
            FROM knowledge_base
        """, (
            demo_user_id,
        ))
        cursor.execute("DROP TABLE knowledge_base")
        cursor.execute("ALTER TABLE knowledge_base_new RENAME TO knowledge_base")

    if not has_unique_index(
        cursor,
        "knowledge_file",
        ["user_id", "kb_name", "file_name"],
    ):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_file_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kb_name TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                docs_count INTEGER NOT NULL,
                update_time TEXT NOT NULL,
                status TEXT DEFAULT 'indexed',
                error TEXT DEFAULT NULL,
                chunk_size INTEGER DEFAULT 300,
                chunk_overlap INTEGER DEFAULT 50,
                content_path TEXT DEFAULT NULL,
                upload_path TEXT DEFAULT NULL,
                user_id INTEGER NOT NULL,
                UNIQUE(user_id, kb_name, file_name)
            )
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO knowledge_file_new (
                id,
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
            SELECT
                id,
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
                COALESCE(user_id, ?)
            FROM knowledge_file
        """, (
            demo_user_id,
        ))
        cursor.execute("DROP TABLE knowledge_file")
        cursor.execute("ALTER TABLE knowledge_file_new RENAME TO knowledge_file")


def init_db():
    """负责 init_db 的函数职责。"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kb_name TEXT UNIQUE NOT NULL,
            embed_model TEXT NOT NULL,
            create_time TEXT NOT NULL
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_file (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kb_name TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        docs_count INTEGER NOT NULL,
        update_time TEXT NOT NULL,
        status TEXT DEFAULT 'indexed',
        error TEXT DEFAULT NULL,
        chunk_size INTEGER DEFAULT 300,
        chunk_overlap INTEGER DEFAULT 50,
        content_path TEXT DEFAULT NULL,
        upload_path TEXT DEFAULT NULL,
        UNIQUE(kb_name, file_name)
    )
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS file_doc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kb_name TEXT NOT NULL,
    file_name TEXT NOT NULL,
    chunk_id INTEGER NOT NULL
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS conversation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    create_time TEXT NOT NULL,
    updated_time TEXT NOT NULL
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    feedback_score INTEGER DEFAULT NULL,
    feedback_reason TEXT DEFAULT NULL,
    metadata TEXT DEFAULT NULL,
    create_time TEXT NOT NULL
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE DEFAULT NULL,
    display_name TEXT DEFAULT NULL,
    avatar_url TEXT DEFAULT NULL,
    auth_provider TEXT NOT NULL,
    password_hash TEXT DEFAULT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_guest INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    language TEXT DEFAULT NULL,
    developer_mode INTEGER NOT NULL DEFAULT 0,
    onboarding_completed INTEGER NOT NULL DEFAULT 0,
    theme TEXT NOT NULL DEFAULT 'light',
    preferred_model TEXT DEFAULT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS auth_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    refresh_token_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT DEFAULT NULL,
    last_used_at TEXT DEFAULT NULL,
    user_agent TEXT DEFAULT NULL,
    ip_address TEXT DEFAULT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS oauth_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    provider_user_id TEXT NOT NULL,
    provider_email TEXT DEFAULT NULL,
    provider_display_name TEXT DEFAULT NULL,
    provider_avatar TEXT DEFAULT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(provider, provider_user_id),
    UNIQUE(user_id, provider),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
)
""")

    cursor.execute("PRAGMA table_info(message)")
    message_columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if "feedback_score" not in message_columns:
        cursor.execute("""
            ALTER TABLE message
            ADD COLUMN feedback_score INTEGER DEFAULT NULL
        """)

    if "feedback_reason" not in message_columns:
        cursor.execute("""
            ALTER TABLE message
            ADD COLUMN feedback_reason TEXT DEFAULT NULL
        """)

    if "metadata" not in message_columns:
        cursor.execute("""
            ALTER TABLE message
            ADD COLUMN metadata TEXT DEFAULT NULL
        """)

    cursor.execute("PRAGMA table_info(users)")
    user_columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    user_migrations = {
        "email": "TEXT DEFAULT NULL",
        "display_name": "TEXT DEFAULT NULL",
        "avatar_url": "TEXT DEFAULT NULL",
        "auth_provider": "TEXT NOT NULL DEFAULT 'email'",
        "password_hash": "TEXT DEFAULT NULL",
        "created_at": "TEXT",
        "updated_at": "TEXT",
        "is_guest": "INTEGER NOT NULL DEFAULT 0",
        "is_active": "INTEGER NOT NULL DEFAULT 1",
    }

    for column, definition in user_migrations.items():
        if column not in user_columns:
            cursor.execute(f"""
                ALTER TABLE users
                ADD COLUMN {column} {definition}
            """)

    cursor.execute("""
        UPDATE users
        SET created_at = COALESCE(created_at, ?),
            updated_at = COALESCE(updated_at, ?)
        WHERE created_at IS NULL OR updated_at IS NULL
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))

    cursor.execute("PRAGMA table_info(user_preferences)")
    preference_columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    preference_migrations = {
        "user_id": "INTEGER NOT NULL DEFAULT 0",
        "language": "TEXT DEFAULT NULL",
        "developer_mode": "INTEGER NOT NULL DEFAULT 0",
        "onboarding_completed": "INTEGER NOT NULL DEFAULT 0",
        "theme": "TEXT NOT NULL DEFAULT 'light'",
        "preferred_model": "TEXT DEFAULT NULL",
        "created_at": "TEXT",
        "updated_at": "TEXT",
    }

    for column, definition in preference_migrations.items():
        if column not in preference_columns:
            cursor.execute(f"""
                ALTER TABLE user_preferences
                ADD COLUMN {column} {definition}
            """)

    cursor.execute("""
        UPDATE user_preferences
        SET created_at = COALESCE(created_at, ?),
            updated_at = COALESCE(updated_at, ?)
        WHERE created_at IS NULL OR updated_at IS NULL
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))

    cursor.execute("PRAGMA table_info(conversation)")
    conversation_columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if "updated_time" not in conversation_columns:
        cursor.execute("""
            ALTER TABLE conversation
            ADD COLUMN updated_time TEXT
        """)
        cursor.execute("""
            UPDATE conversation
            SET updated_time = create_time
            WHERE updated_time IS NULL
        """)

    ownership_migrations = {
        "conversation": "INTEGER DEFAULT NULL",
        "message": "INTEGER DEFAULT NULL",
        "knowledge_base": "INTEGER DEFAULT NULL",
        "knowledge_file": "INTEGER DEFAULT NULL",
        "file_doc": "INTEGER DEFAULT NULL",
    }

    for table_name, definition in ownership_migrations.items():
        cursor.execute(f"PRAGMA table_info({table_name})")
        table_columns = [
            row[1]
            for row in cursor.fetchall()
        ]

        if "user_id" not in table_columns:
            cursor.execute(f"""
                ALTER TABLE {table_name}
                ADD COLUMN user_id {definition}
            """)

    cursor.execute("PRAGMA table_info(knowledge_file)")
    knowledge_file_columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    knowledge_file_migrations = {
        "status": "TEXT DEFAULT 'indexed'",
        "error": "TEXT DEFAULT NULL",
        "chunk_size": "INTEGER DEFAULT 300",
        "chunk_overlap": "INTEGER DEFAULT 50",
        "content_path": "TEXT DEFAULT NULL",
        "upload_path": "TEXT DEFAULT NULL",
    }

    for column, definition in knowledge_file_migrations.items():
        if column not in knowledge_file_columns:
            cursor.execute(f"""
                ALTER TABLE knowledge_file
                ADD COLUMN {column} {definition}
            """)


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
    demo_user_id = cursor.fetchone()[0]

    cursor.execute("""
        INSERT OR IGNORE INTO user_preferences (
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
        demo_user_id,
        None,
        0,
        0,
        "light",
        None,
        now,
        now,
    ))

    for table_name in (
        "conversation",
        "message",
        "knowledge_base",
        "knowledge_file",
        "file_doc",
    ):
        cursor.execute(f"""
            UPDATE {table_name}
            SET user_id = ?
            WHERE user_id IS NULL
        """, (
            demo_user_id,
        ))

    ensure_user_scoped_unique_constraints(cursor, demo_user_id)

    conn.commit()
    conn.close()


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


def create_conversation(title=None, user_id=None):
    """负责 create_conversation 的函数职责。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    conversation_title = title or "New Conversation"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO conversation (
            title,
            create_time,
            updated_time,
            user_id
        )
        VALUES (?, ?, ?, ?)
    """, (
        conversation_title,
        now,
        now,
        resolved_user_id,
    ))

    conversation_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return conversation_id


def list_conversations(user_id=None):
    """负责 list_conversations 的函数职责。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, create_time, updated_time
        FROM conversation
        WHERE user_id = ?
        ORDER BY updated_time DESC, id DESC
    """, (
        resolved_user_id,
    ))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "title": row[1],
            "create_time": row[2],
            "updated_time": row[3]
        }
        for row in rows
    ]


def get_conversation(conversation_id, user_id=None):
    """负责 get_conversation 的函数职责。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, create_time, updated_time
        FROM conversation
        WHERE id = ? AND user_id = ?
    """, (
        conversation_id,
        resolved_user_id,
    ))

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "title": row[1],
        "create_time": row[2],
        "updated_time": row[3]
    }


def update_conversation_title(conversation_id, title, user_id=None):
    """负责 update_conversation_title 的函数职责。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE conversation
        SET title = ?,
            updated_time = ?
        WHERE id = ? AND user_id = ?
    """, (
        title,
        now,
        conversation_id,
        resolved_user_id,
    ))

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    if not updated:
        return None

    return get_conversation(conversation_id, user_id=resolved_user_id)


def delete_conversation(conversation_id, user_id=None):
    """负责 delete_conversation 的函数职责。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM conversation
        WHERE id = ? AND user_id = ?
    """, (
        conversation_id,
        resolved_user_id,
    ))

    if cursor.fetchone() is None:
        conn.close()
        return False

    cursor.execute("""
        DELETE FROM message
        WHERE conversation_id = ? AND user_id = ?
    """, (
        conversation_id,
        resolved_user_id,
    ))

    cursor.execute("""
        DELETE FROM conversation
        WHERE id = ? AND user_id = ?
    """, (
        conversation_id,
        resolved_user_id,
    ))

    conn.commit()
    conn.close()

    return True


def encode_metadata(metadata):
    """负责 encode_metadata 的函数职责。"""
    if metadata is None:
        return None

    return json.dumps(metadata, ensure_ascii=False)


def decode_metadata(metadata_text):
    """负责 decode_metadata 的函数职责。"""
    if not metadata_text:
        return None

    try:
        return json.loads(metadata_text)
    except (TypeError, json.JSONDecodeError):
        return None


def save_message(conversation_id, role, content, metadata=None, user_id=None):
    # 每次写消息同步更新时间；assistant 的 sources/agent trace 统一放 metadata 以便历史回放。
    """负责 save_message 的函数职责。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadata_text = encode_metadata(metadata)

    cursor.execute("""
        SELECT id
        FROM conversation
        WHERE id = ? AND user_id = ?
    """, (
        conversation_id,
        resolved_user_id,
    ))

    if cursor.fetchone() is None:
        conn.close()
        return None

    cursor.execute("""
        INSERT INTO message (
            conversation_id,
            role,
            content,
            metadata,
            create_time,
            user_id
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        conversation_id,
        role,
        content,
        metadata_text,
        now,
        resolved_user_id,
    ))

    message_id = cursor.lastrowid

    cursor.execute("""
        UPDATE conversation
        SET updated_time = ?
        WHERE id = ? AND user_id = ?
    """, (
        now,
        conversation_id,
        resolved_user_id,
    ))

    conn.commit()
    conn.close()

    return message_id


def get_conversation_messages(conversation_id, user_id=None):
    # 读取历史时把持久化的 sources 恢复到顶层字段，保持前端消息结构不变。
    """负责 get_conversation_messages 的函数职责。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            role,
            content,
            create_time,
            feedback_score,
            feedback_reason,
            metadata
        FROM message
        WHERE conversation_id = ? AND user_id = ?
        ORDER BY id
    """, (
        conversation_id,
        resolved_user_id,
    ))

    rows = cursor.fetchall()
    conn.close()

    messages = []

    for row in rows:
        metadata = decode_metadata(row[6])
        message = {
            "id": row[0],
            "role": row[1],
            "content": row[2],
            "create_time": row[3],
            "feedback_score": row[4],
            "feedback_reason": row[5],
            "metadata": metadata
        }

        if isinstance(metadata, dict) and isinstance(metadata.get("sources"), list):
            message["sources"] = metadata["sources"]

        messages.append(message)

    return messages


def update_message_feedback(message_id, score, reason=None, user_id=None):
    """负责 update_message_feedback 的函数职责。"""
    resolved_user_id = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE message
        SET feedback_score = ?,
            feedback_reason = ?
        WHERE id = ? AND user_id = ?
    """, (
        score,
        reason,
        message_id,
        resolved_user_id,
    ))

    updated = cursor.rowcount

    conn.commit()
    conn.close()

    return updated > 0


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
