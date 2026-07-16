import json
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mini.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
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
    

    conn.commit()
    conn.close()


def create_default_kb():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO knowledge_base (
            kb_name,
            embed_model,
            create_time
        )
        VALUES (?, ?, ?)
    """, (
        "default",
        "all-MiniLM-L6-v2",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def list_kbs():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, kb_name, embed_model, create_time
        FROM knowledge_base
    """)

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

def create_kb(kb_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO knowledge_base (
            kb_name,
            embed_model,
            create_time
        )
        VALUES (?, ?, ?)
    """, (
        kb_name,
        "all-MiniLM-L6-v2",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def create_conversation(title=None):
    conn = get_connection()
    cursor = conn.cursor()

    conversation_title = title or "New Conversation"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO conversation (
            title,
            create_time,
            updated_time
        )
        VALUES (?, ?, ?)
    """, (
        conversation_title,
        now,
        now
    ))

    conversation_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return conversation_id


def list_conversations():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, create_time, updated_time
        FROM conversation
        ORDER BY updated_time DESC, id DESC
    """)

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


def get_conversation(conversation_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, create_time, updated_time
        FROM conversation
        WHERE id = ?
    """, (
        conversation_id,
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


def update_conversation_title(conversation_id, title):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE conversation
        SET title = ?,
            updated_time = ?
        WHERE id = ?
    """, (
        title,
        now,
        conversation_id
    ))

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    if not updated:
        return None

    return get_conversation(conversation_id)


def delete_conversation(conversation_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM conversation
        WHERE id = ?
    """, (
        conversation_id,
    ))

    if cursor.fetchone() is None:
        conn.close()
        return False

    cursor.execute("""
        DELETE FROM message
        WHERE conversation_id = ?
    """, (
        conversation_id,
    ))

    cursor.execute("""
        DELETE FROM conversation
        WHERE id = ?
    """, (
        conversation_id,
    ))

    conn.commit()
    conn.close()

    return True


def encode_metadata(metadata):
    if metadata is None:
        return None

    return json.dumps(metadata, ensure_ascii=False)


def decode_metadata(metadata_text):
    if not metadata_text:
        return None

    try:
        return json.loads(metadata_text)
    except (TypeError, json.JSONDecodeError):
        return None


def save_message(conversation_id, role, content, metadata=None):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadata_text = encode_metadata(metadata)

    cursor.execute("""
        INSERT INTO message (
            conversation_id,
            role,
            content,
            metadata,
            create_time
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        conversation_id,
        role,
        content,
        metadata_text,
        now
    ))

    message_id = cursor.lastrowid

    cursor.execute("""
        UPDATE conversation
        SET updated_time = ?
        WHERE id = ?
    """, (
        now,
        conversation_id
    ))

    conn.commit()
    conn.close()

    return message_id


def get_conversation_messages(conversation_id):
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
        WHERE conversation_id = ?
        ORDER BY id
    """, (
        conversation_id,
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


def update_message_feedback(message_id, score, reason=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE message
        SET feedback_score = ?,
            feedback_reason = ?
        WHERE id = ?
    """, (
        score,
        reason,
        message_id
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
):
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
            upload_path
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    ))

    conn.commit()
    conn.close()


def update_file_status(kb_name, file_name, status, error=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE knowledge_file
        SET status = ?,
            error = ?,
            update_time = ?
        WHERE kb_name = ? AND file_name = ?
    """, (
        status,
        error,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        kb_name,
        file_name,
    ))

    conn.commit()
    conn.close()


def delete_file_record(kb_name, file_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM knowledge_file
        WHERE kb_name = ? AND file_name = ?
    """, (
        kb_name,
        file_name
    ))

    conn.commit()
    conn.close()

def list_file_records(kb_name):
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
        WHERE kb_name = ?
    """, (
        kb_name,
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

def add_file_doc(kb_name, file_name, chunk_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO file_doc (
            kb_name,
            file_name,
            chunk_id
        )
        VALUES (?, ?, ?)
    """, (
        kb_name,
        file_name,
        int(chunk_id),
    ))

    conn.commit()
    conn.close()
    print(f"INSERT FILE_DOC -> {file_name} : {chunk_id}")

def delete_file_docs(kb_name, file_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM file_doc
        WHERE kb_name = ? AND file_name = ?
    """, (
        kb_name,
        file_name
    ))

    conn.commit()
    conn.close()

def list_file_docs(kb_name, file_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT chunk_id
        FROM file_doc
        WHERE kb_name = ? AND file_name = ?
        ORDER BY chunk_id
    """, (
        kb_name,
        file_name
    ))

    rows = cursor.fetchall()
    conn.close()

    return [
        {"chunk_id": row[0]}
        for row in rows
    ]

def delete_file_docs_by_kb(kb_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM file_doc
        WHERE kb_name = ?
    """, (
        kb_name,
    ))

    conn.commit()
    conn.close()


def delete_files_by_kb(kb_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM knowledge_file
        WHERE kb_name = ?
    """, (
        kb_name,
    ))

    conn.commit()
    conn.close()


def delete_kb_record(kb_name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM knowledge_base
        WHERE kb_name = ?
    """, (
        kb_name,
    ))

    conn.commit()
    conn.close()
