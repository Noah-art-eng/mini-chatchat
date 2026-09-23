import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone


STARTED_AT = time.time()
STARTED_AT_ISO = datetime.fromtimestamp(STARTED_AT, timezone.utc).isoformat()


def configure_logging():
    """负责 configure_logging 的函数职责。"""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(message)s",
    )


def new_request_id():
    """负责 new_request_id 的函数职责。"""
    return uuid.uuid4().hex


def log_json(event: str, **fields):
    """负责 log_json 的函数职责。"""
    payload = {
        "event": event,
        "service": "mini-chatchat",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    logging.getLogger("mini-chatchat").info(json.dumps(payload, ensure_ascii=False))


def get_runtime_metadata():
    """负责 get_runtime_metadata 的函数职责。"""
    return {
        "version": os.getenv("APP_VERSION", "1.0.0-rc.1"),
        "build_time": os.getenv("BUILD_TIME", ""),
        "git_commit": os.getenv("GIT_COMMIT", ""),
        "started_at": STARTED_AT_ISO,
        "uptime_seconds": int(time.time() - STARTED_AT),
        "environment": (
            os.getenv("APP_ENV")
            or os.getenv("ENVIRONMENT")
            or os.getenv("MINI_CHATCHAT_ENV")
            or "development"
        ),
    }
