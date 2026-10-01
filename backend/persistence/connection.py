"""SQLite 连接创建与 DB 方法统一清理。"""

import os
import sqlite3
from contextvars import ContextVar
from functools import wraps


_ACTIVE_CONNECTIONS = ContextVar("active_db_connections", default=None)


def connection_scope(func):
    """确保一个 DB 方法创建的连接在返回或抛异常时都被关闭。"""
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
    """为指定 SQLite 文件创建启用外键约束且纳入统一清理的连接。"""
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
