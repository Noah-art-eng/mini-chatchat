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
    """负责 get_user_slug 的函数职责。"""
    return DEMO_USER_SLUG if user_id is None else f"user_{user_id}"


def get_user_root(user_id=None):
    """负责 get_user_root 的函数职责。"""
    return os.path.join(USERS_ROOT, get_user_slug(user_id))


def get_user_kb_root(user_id=None):
    """负责 get_user_kb_root 的函数职责。"""
    return os.path.join(get_user_root(user_id), "knowledge_bases")


def get_user_temp_root(user_id=None):
    """负责 get_user_temp_root 的函数职责。"""
    return os.path.join(get_user_root(user_id), "temp")


def ensure_user_directories(user_id=None):
    """负责 ensure_user_directories 的函数职责。"""
    for path in (
        get_user_root(user_id),
        get_user_kb_root(user_id),
        get_user_temp_root(user_id),
    ):
        os.makedirs(path, exist_ok=True)


def is_legacy_kb_directory(path, name):
    """负责 is_legacy_kb_directory 的函数职责。"""
    if name in RESERVED_DATA_DIRS:
        return False

    if not os.path.isdir(path):
        return False

    return any(
        os.path.isdir(os.path.join(path, dirname))
        for dirname in ("content", "uploads", "vector_store")
    )


def migrate_legacy_demo_files():
    """负责 migrate_legacy_demo_files 的函数职责。"""
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
