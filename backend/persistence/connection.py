"""SQLite 连接创建与 DB 方法统一清理。"""

import os
import sqlite3
from contextvars import ContextVar
from functools import wraps


_ACTIVE_CONNECTIONS = ContextVar("active_db_connections", default=None)


def connection_scope(func):
    """为一次持久化操作集中管理它创建的 SQLite 连接。

    正常返回时统一关闭；任意异常先回滚再关闭。业务函数不需要在每个分支重复清理，
    也不会因为中途抛错泄漏连接。
    """
    @wraps(func)
    def wrapped(*args, **kwargs):
        connections = []
        token = _ACTIVE_CONNECTIONS.set(connections)
        try:
            return func(*args, **kwargs)
        except BaseException:
            for connection in reversed(connections):
                try:
                    connection.rollback()
                except sqlite3.Error:
                    pass
            raise
        finally:
            for connection in reversed(connections):
                try:
                    connection.close()
                except sqlite3.Error:
                    pass
            _ACTIVE_CONNECTIONS.reset(token)

    return wrapped


def open_connection(db_path):
    """创建启用外键约束的 SQLite 连接，并登记到当前 connection_scope。

    SQLite 的 foreign_keys 设置按连接生效，所以每个新连接都必须执行 PRAGMA，
    不能只在数据库初始化时设置一次。
    """
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
    except BaseException:
        connection.close()
        raise

    active_connections = _ACTIVE_CONNECTIONS.get()
    if active_connections is not None:
        active_connections.append(connection)
    return connection
