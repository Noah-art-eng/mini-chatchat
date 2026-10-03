import os
import shutil

DEMO_USER_EMAIL = "demo@local"
DEMO_USER_SLUG = "demo"
DATA_ROOT = os.getenv("MINI_CHATCHAT_DATA_ROOT", "data")
USERS_ROOT = os.path.join(DATA_ROOT, "users")
DEMO_USER_ROOT = os.path.join(USERS_ROOT, DEMO_USER_SLUG)
DEMO_KB_ROOT = os.path.join(DEMO_USER_ROOT, "knowledge_bases")
DEMO_TEMP_ROOT = os.path.join(DEMO_USER_ROOT, "temp")

RESERVED_DATA_DIRS = {
    "temp",
    "users",
}


def get_user_slug(user_id=None):
    """把数据库 user_id 转成稳定目录名；访客统一落到 demo 范围。"""
    return DEMO_USER_SLUG if user_id is None else f"user_{user_id}"


def get_user_root(user_id=None):
    """返回当前用户全部运行数据的根目录。"""
    return os.path.join(USERS_ROOT, get_user_slug(user_id))


def get_user_kb_root(user_id=None):
    """返回当前用户的正式知识库目录，隔离不同用户的文件和索引。"""
    return os.path.join(get_user_root(user_id), "knowledge_bases")


def get_user_temp_root(user_id=None):
    """返回当前用户的临时知识库目录。"""
    return os.path.join(get_user_root(user_id), "temp")


def ensure_user_directories(user_id=None):
    """在第一次访问用户范围时补齐正式知识库和临时目录。"""
    for path in (
        get_user_root(user_id),
        get_user_kb_root(user_id),
        get_user_temp_root(user_id),
    ):
        os.makedirs(path, exist_ok=True)


def is_legacy_kb_directory(path, name):
    """识别旧版本直接放在 data 根目录下的知识库结构。"""
    if name in RESERVED_DATA_DIRS:
        return False

    if not os.path.isdir(path):
        return False

    return any(
        os.path.isdir(os.path.join(path, dirname))
        for dirname in ("content", "uploads", "vector_store")
    )


def migrate_legacy_demo_files():
    """把旧版 demo 数据复制到新的用户隔离目录，同时保留原文件作兼容。"""
    ensure_user_directories()

    if not os.path.isdir(DATA_ROOT):
        return

    for name in os.listdir(DATA_ROOT):
        legacy_path = os.path.join(DATA_ROOT, name)

        if not is_legacy_kb_directory(legacy_path, name):
            continue

        target_path = os.path.join(DEMO_KB_ROOT, name)

        if os.path.exists(target_path):
            continue

        shutil.copytree(legacy_path, target_path)

    legacy_temp = os.path.join(DATA_ROOT, "temp")
    if os.path.isdir(legacy_temp):
        for name in os.listdir(legacy_temp):
            source = os.path.join(legacy_temp, name)
            target = os.path.join(DEMO_TEMP_ROOT, name)

            if os.path.exists(target):
                continue

            if os.path.isdir(source):
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
