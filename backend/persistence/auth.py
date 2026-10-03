"""User、OAuth、Session 与 Preferences 的 SQLite 持久化实现。"""

from datetime import datetime


def row_to_user(row):
    """把 SQLite 用户行转换成持久化层统一使用的字典。"""
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
    """移除密码摘要等认证字段，只返回可以交给 API 的用户信息。"""
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


def get_user_by_id(get_connection, user_id):
    """按用户编号读取公开用户信息；找不到时返回 None。"""
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


def get_user_by_email(get_connection, email):
    """按规范化邮箱查找用户，供登录和重复注册检查使用。"""
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


def get_user_auth_by_email(get_connection, email):
    """读取登录校验需要的用户记录和密码摘要，不把该结构直接返回前端。"""
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
    get_connection,
    email=None,
    display_name=None,
    avatar_url=None,
    auth_provider="email",
    password_hash=None,
    is_guest=False,
    is_active=True,
):
    """在一个事务中创建用户、认证方式和默认偏好，任一步失败都会回滚。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 先创建身份主体，再用生成的 user_id 建立默认偏好。两条记录在同一次提交中生效。
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

    return get_user_by_id(get_connection, user_id)


def get_user_password_hash(get_connection, user_id):
    """只读取密码校验需要的摘要，避免其他查询默认携带认证数据。"""
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


def create_email_user(get_connection, email, password_hash, display_name=None):
    """创建邮箱登录用户，并保存密码摘要而不是明文密码。"""
    return create_user(
        get_connection,
        email=email,
        display_name=display_name or email,
        auth_provider="email",
        password_hash=password_hash,
        is_guest=False,
        is_active=True,
    )


def set_user_active(get_connection, user_id, is_active):
    """启用或停用用户；停用后认证依赖会拒绝该用户继续访问。"""
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


def update_user_account(get_connection, user_id, display_name):
    """更新当前用户可修改的账户资料，并返回最新公开信息。"""
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

    return get_user_by_id(get_connection, user_id) if updated else None


def row_to_oauth_account(row):
    """把 OAuth 账号查询结果整理成持久化层统一字典。"""
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
    """只保留前端账户页需要的 OAuth 绑定信息。"""
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


def get_oauth_account(get_connection, provider, provider_user_id):
    """按 Provider 用户标识查找绑定关系，供 OAuth 登录定位本地用户。"""
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


def get_oauth_account_for_user(get_connection, user_id, provider):
    """读取某个用户与指定 Provider 的绑定，供绑定和解绑校验使用。"""
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


def list_oauth_accounts_for_user(get_connection, user_id):
    """返回用户全部 OAuth 绑定，但不暴露 Provider access token。"""
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
    get_connection,
    user_id,
    provider,
    provider_user_id,
    provider_email=None,
    provider_display_name=None,
    provider_avatar=None,
):
    """创建或更新 OAuth 绑定，并保持 Provider 账号到本地用户的唯一关系。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Provider + provider_user_id 是外部身份唯一键。重复回调只更新资料，不创建第二个绑定。
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
    return get_oauth_account(get_connection, provider, provider_user_id)


def delete_oauth_account_for_user(get_connection, user_id, provider):
    """删除当前用户的指定 OAuth 绑定；调用方会先确认仍有其他登录方式。"""
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


def user_login_method_count(get_connection, user_id):
    """统计用户仍可使用的密码或 OAuth 登录方式，避免解绑最后一种方式。"""
    password_hash = get_user_password_hash(get_connection, user_id)
    oauth_count = len(list_oauth_accounts_for_user(get_connection, user_id))
    return (1 if password_hash else 0) + oauth_count


def create_auth_session(
    get_connection,
    session_id,
    user_id,
    refresh_token_hash,
    expires_at,
    user_agent=None,
    ip_address=None,
):
    """保存登录 Session、refresh token 摘要和过期时间。"""
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

    return get_auth_session(get_connection, session_id)


def row_to_auth_session(row):
    """把数据库会话行转换成认证层使用的结构。"""
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


def get_auth_session(get_connection, session_id):
    """按 session_id 读取 refresh token 对应的数据库会话。"""
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


def list_auth_sessions_by_user(get_connection, user_id):
    """返回用户的登录设备会话，供账户页展示和撤销。"""
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
    get_connection,
    session_id,
    refresh_token_hash,
    expires_at,
):
    """原子轮换活动 Session 的 refresh token 摘要和过期时间。"""
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


def revoke_auth_session(get_connection, session_id):
    """撤销一个数据库会话，使对应 refresh token 立即失效。"""
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


def revoke_auth_session_for_user(get_connection, user_id, session_id):
    """只在会话属于当前用户时撤销，避免跨用户操作。"""
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


def revoke_other_auth_sessions(get_connection, user_id, current_session_id):
    """保留当前会话并撤销用户其他设备会话。"""
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


def revoke_user_auth_sessions(get_connection, user_id):
    """撤销用户全部会话，供全端退出使用。"""
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


def cleanup_expired_auth_sessions(get_connection):
    """删除已经过期的会话记录，避免会话表持续增长。"""
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


def get_user_preferences(get_connection, user_id):
    """读取用户界面偏好；没有记录时返回项目默认值。"""
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
    get_connection,
    user_id,
    language=None,
    developer_mode=False,
    onboarding_completed=False,
    theme="light",
    preferred_model=None,
):
    """创建或更新用户偏好；未提供的字段沿用数据库现值。"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # user_id 唯一约束让首次保存走 INSERT，之后走 UPDATE；调用方始终得到一份完整偏好。
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

    return get_user_preferences(get_connection, user_id)
