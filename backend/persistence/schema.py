"""Mini ChatChat SQLite schema 初始化与兼容迁移。"""

from datetime import datetime


def has_unique_index(cursor, table_name, expected_columns):
    """检查旧数据库是否已经具有目标唯一约束，避免重复迁移。"""
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
    """把旧版全局唯一约束迁移为 user_id 范围内唯一。

    旧记录缺少 user_id 时归入 demo 用户，使升级后的知识库和文件查询仍能找到原数据。
    """
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


def init_db(get_connection, demo_user_email):
    """初始化 SQLite schema，并按顺序执行兼容迁移和默认 demo 用户创建。

    入口可重复执行。所有建表、迁移和索引更新使用同一连接提交，失败时由连接层回滚。
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 第一阶段建立全新数据库需要的业务表。IF NOT EXISTS 让启动时重复调用保持安全。
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

    # 第二阶段检查旧数据库缺少的列并就地补齐，保留用户已有数据。
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

    # 早期版本的数据没有 user_id。先补列，后面统一归到 demo 用户，避免升级后失联。
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


    # 第三阶段确保兼容用的 demo 用户和偏好存在，再迁移旧的无归属记录。
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
        demo_user_email,
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
        demo_user_email,
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

    # 最后把旧的全局唯一约束迁成用户范围唯一约束，提交后业务 CRUD 才开始使用。
    ensure_user_scoped_unique_constraints(cursor, demo_user_id)

    conn.commit()
    conn.close()
