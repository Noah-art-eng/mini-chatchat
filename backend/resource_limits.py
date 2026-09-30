"""集中管理上传阶段的资源上限和分块落盘。"""

import math
import os
import shutil
import tempfile
from dataclasses import dataclass


MIB = 1024 * 1024


def _mib_from_env(name: str, default: int) -> int:
    """读取正数 MiB 环境变量，并在未配置时使用项目默认值。"""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default * MIB

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value * MIB


def _positive_float_from_env(name: str, default: float) -> float:
    """读取有限正浮点配置；非法配置直接阻止服务启动。"""
    raw_value = os.getenv(name)
    if raw_value is None:
        return float(default)

    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc

    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number greater than zero")
    return value


MAX_DOCUMENT_UPLOAD_BYTES = _mib_from_env(
    "MINI_CHATCHAT_MAX_DOCUMENT_UPLOAD_MIB",
    1024,
)
MAX_TEMP_UPLOAD_BYTES = _mib_from_env(
    "MINI_CHATCHAT_MAX_TEMP_UPLOAD_MIB",
    1024,
)
MAX_ZIP_UPLOAD_BYTES = _mib_from_env(
    "MINI_CHATCHAT_MAX_ZIP_UPLOAD_MIB",
    2048,
)
UPLOAD_CHUNK_BYTES = _mib_from_env("MINI_CHATCHAT_UPLOAD_CHUNK_MIB", 1)

MAX_ZIP_MEMBER_COUNT = int(os.getenv("MINI_CHATCHAT_MAX_ZIP_MEMBERS", "10000"))
MAX_ZIP_MEMBER_BYTES = _mib_from_env("MINI_CHATCHAT_MAX_ZIP_MEMBER_MIB", 2048)
MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES = _mib_from_env(
    "MINI_CHATCHAT_MAX_ZIP_EXTRACTED_MIB",
    8192,
)
ZIP_RATIO_MIN_UNCOMPRESSED_BYTES = _mib_from_env(
    "MINI_CHATCHAT_ZIP_RATIO_MIN_MIB",
    1,
)
MAX_ZIP_COMPRESSION_RATIO = _positive_float_from_env(
    "MINI_CHATCHAT_MAX_ZIP_COMPRESSION_RATIO",
    100,
)


class ResourceLimitError(ValueError):
    """表示上传或 ZIP 内容超过项目配置的资源上限。"""


@dataclass(frozen=True)
class StagedUpload:
    """记录已完整写入 staging 文件的路径和实际字节数。"""

    path: str
    size: int


def remove_file_quietly(path: str | None) -> None:
    """清理本轮创建的临时文件；文件已不存在时无需额外报错。"""
    if path and os.path.exists(path):
        os.remove(path)


async def stage_upload(
    upload_file,
    *,
    max_bytes: int,
    error_message: str,
    chunk_bytes: int = UPLOAD_CHUNK_BYTES,
    directory: str | None = None,
    suffix: str = "",
) -> StagedUpload:
    """按固定大小读取 UploadFile，并写入可在失败时清理的 staging 文件。"""
    if max_bytes < 0 or chunk_bytes <= 0:
        raise ValueError("upload limits must be positive")

    temp_file = tempfile.NamedTemporaryFile(
        prefix="mini_chatchat_upload_",
        suffix=suffix,
        dir=directory,
        delete=False,
    )
    staged_path = temp_file.name
    temp_file.close()
    total_bytes = 0

    try:
        with open(staged_path, "wb") as output:
            while True:
                chunk = await upload_file.read(chunk_bytes)
                if not chunk:
                    break

                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise ResourceLimitError(error_message)
                output.write(chunk)
    except Exception:
        remove_file_quietly(staged_path)
        raise

    return StagedUpload(path=staged_path, size=total_bytes)


def install_staged_file(
    staged_path: str,
    target_path: str,
    *,
    chunk_bytes: int = UPLOAD_CHUNK_BYTES,
) -> None:
    """在目标目录生成完整临时副本，再原子替换正式文件。"""
    target_directory = os.path.dirname(target_path)
    os.makedirs(target_directory, exist_ok=True)
    target_stage = tempfile.NamedTemporaryFile(
        prefix=".mini_chatchat_staging_",
        dir=target_directory,
        delete=False,
    )
    target_stage_path = target_stage.name
    target_stage.close()

    try:
        with open(staged_path, "rb") as source, open(target_stage_path, "wb") as target:
            shutil.copyfileobj(source, target, length=chunk_bytes)
        os.replace(target_stage_path, target_path)
    except Exception:
        remove_file_quietly(target_stage_path)
        raise
