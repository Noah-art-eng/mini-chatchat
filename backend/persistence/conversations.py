"""Conversation、Message 与 Feedback 的 SQLite 持久化实现。"""

import json
from datetime import datetime


def create_conversation(get_connection, resolve_user_id, title=None, user_id=None):
    """为目标用户创建会话，并返回后续消息写入使用的 conversation_id。"""
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


def list_conversations(get_connection, resolve_user_id, user_id=None):
    """按最近更新时间列出当前用户的会话，供前端会话列表使用。"""
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


def get_conversation(get_connection, resolve_user_id, conversation_id, user_id=None):
    """按 conversation_id 和 user_id 读取会话，避免跨用户访问。"""
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


def update_conversation_title(
    get_connection,
    resolve_user_id,
    conversation_id,
    title,
    user_id=None,
):
    """只修改属于当前用户的会话标题；不存在或越权时返回 None。"""
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

    return get_conversation(
        get_connection,
        resolve_user_id,
        conversation_id,
        user_id=resolved_user_id,
    )


def delete_conversation(get_connection, resolve_user_id, conversation_id, user_id=None):
    """删除当前用户的会话及其全部消息。"""
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
    """把 Sources、Agent trace 等消息附加信息编码成 SQLite 可保存的 JSON。"""
    if metadata is None:
        return None

    return json.dumps(metadata, ensure_ascii=False)


def decode_metadata(metadata_text):
    """读取消息 metadata；旧数据为空或损坏时安全回退为空字典。"""
    if not metadata_text:
        return None

    try:
        return json.loads(metadata_text)
    except (TypeError, json.JSONDecodeError):
        return None


def save_message(
    get_connection,
    resolve_user_id,
    conversation_id,
    role,
    content,
    metadata=None,
    user_id=None,
):
    """保存消息并更新会话时间。

    助手消息的 Sources、Agent trace 等结构化信息写入 metadata，页面刷新后可以恢复
    当时展示的回答上下文。
    """
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


def get_conversation_messages(
    get_connection,
    resolve_user_id,
    conversation_id,
    user_id=None,
):
    # 读取历史时把持久化的 sources 恢复到顶层字段，保持前端消息结构不变。
    """确认会话属于当前用户后按时间顺序返回消息和 metadata。"""
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


def update_message_feedback(
    get_connection,
    resolve_user_id,
    message_id,
    score,
    reason=None,
    user_id=None,
):
    """只更新当前用户助手消息的反馈，防止通过 message_id 跨用户修改。"""
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
