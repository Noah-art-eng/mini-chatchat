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

def upsert_file_record(
    kb_name,
    file_name,
    file_size,
    docs_count
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO knowledge_file (
            kb_name,
            file_name,
            file_size,
            docs_count,
            update_time
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        kb_name,
        file_name,
        file_size,
        docs_count,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        SELECT file_name, file_size, docs_count, update_time
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
            "time": row[3]
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
