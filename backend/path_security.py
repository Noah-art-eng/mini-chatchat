"""集中检查外部传入的文件名和知识库名称，防止 Path Traversal。

Path Traversal（路径穿越）可以简单理解为：程序本来只能操作规定文件夹，
有人却在 filename 或 kb_name 中放入 ``../``、绝对路径等内容，想跑到外面
读取或写入其他文件。本模块分两步拦截这种输入：

1. 先检查用户提供的名称，确认它只是普通的 filename 或 kb_name；
2. 拼出完整路径后再检查 realpath（文件系统最终会访问的真实路径），确认目标
   仍在规定文件夹里。

这里会直接拒绝非法输入，不会用 ``basename`` 偷偷取出最后一段名称。例如，
``../report.pdf`` 不会被改成 ``report.pdf`` 后继续执行。那样会掩盖有问题的请求，
还可能覆盖规定文件夹里原本存在的同名文件。
"""

# ``os`` 是 Python 操作文件和路径时常用的标准库。``ntpath`` 按 Windows 的
# 路径规则工作，所以服务即使运行在 Linux/macOS 上，也能认出 ``C:\file.txt``。
import ntpath
import os


class PathValidationError(ValueError):
    """表示传入的名称不安全，或者最终路径已经跑到规定文件夹之外。"""


def _is_safe_name(value: str) -> bool:
    """接收一个外部名称，返回它能否作为单独的文件名或文件夹名。

    返回值只有 True 或 False，原始输入不会被修改。这里同时检查 ``/`` 和
    ``\\``，是为了让 Linux、macOS 和 Windows 下使用同一套规则。
    """
    return (
        isinstance(value, str)  # filename 和 kb_name 必须是字符串
        and bool(value)  # 拒绝空字符串
        and value not in {".", ".."}  # 拒绝当前文件夹和上一级文件夹
        and ".." not in value  # 拒绝通过 ../ 一类写法向上跳出文件夹
        and "\x00" not in value  # 拒绝可能干扰底层文件 API 的空字符
        and "/" not in value  # 拒绝 Linux/macOS 的路径分隔符
        and "\\" not in value  # 拒绝 Windows 的路径分隔符
        and not os.path.isabs(value)  # 拒绝当前系统格式的绝对路径
        and not ntpath.isabs(value)  # 在非 Windows 系统上也拒绝 Windows 绝对路径
    )


def is_safe_filename(filename: str) -> bool:
    """接收 filename，返回它是否能安全地用于上传或文档操作。"""
    return _is_safe_name(filename)


def is_safe_kb_name(kb_name: str) -> bool:
    """接收 kb_name，返回它是否能安全地用作知识库文件夹名称。"""
    return _is_safe_name(kb_name)


def validate_filename(filename: str) -> str:
    """检查 filename；合法就原样返回，非法就抛出固定类型的异常。

    ``raise`` 表示立刻停止当前操作，之后由 API 层把异常转换成 400 响应。
    这里不只返回 False，是为了避免调用方忘记检查结果，又继续执行写文件操作。
    """
    if not is_safe_filename(filename):
        raise PathValidationError("invalid filename")
    return filename


def validate_kb_name(kb_name: str) -> str:
    """检查 kb_name；合法就原样返回，非法就抛出固定类型的异常。"""
    if not is_safe_kb_name(kb_name):
        raise PathValidationError("invalid kb_name")
    return kb_name


def safe_join(root, name: str, *, field_name: str) -> str:
    """把规定文件夹和外部名称拼成完整路径，并再次确认结果没有跑到外面。

    Args:
        root: 允许程序操作的文件夹，可以是字符串或 ``pathlib.Path`` 对象。
        name: 外部传入的 filename 或 kb_name。
        field_name: 告诉函数当前检查的是 filename 还是 kb_name。

    Returns:
        文件系统最终会访问的完整路径，例如
        ``/MiniChatChat/uploads/report.pdf``，并保证它位于 ``root`` 里面。

    Raises:
        PathValidationError: 名称非法，或最终路径跑到了规定文件夹外面。
        ValueError: ``field_name`` 既不是 filename，也不是 kb_name。
    """
    # 第一层先检查用户直接传来的名称；发现问题就拒绝，不替用户偷偷改名。
    if field_name == "filename":
        validate_filename(name)
    elif field_name == "kb_name":
        validate_kb_name(name)
    else:
        raise ValueError("unsupported path field")

    # os.fspath() 把 str、pathlib.Path 等路径写法转成文件系统可以使用的形式。
    # os.path.join() 负责拼路径，例如把 ``/MiniChatChat/uploads`` 和
    # ``report.pdf`` 拼成 ``/MiniChatChat/uploads/report.pdf``。
    # realpath() 会得到文件系统最终访问的真实位置，也会处理 ``..`` 和符号链接。
    # 这样即使表面路径在 uploads 中，实际指向外部文件夹，也能在下一步发现。
    resolved_root = os.path.realpath(os.fspath(root))
    target_path = os.path.realpath(os.path.join(resolved_root, name))

    # commonpath() 找出两个路径共同的文件夹。例如 root 是
    # ``/MiniChatChat/uploads``，目标是 ``/MiniChatChat/uploads/report.pdf``，
    # 共同部分仍是 root，说明目标没有跑出去。不能用字符串 startswith 判断，
    # 因为它会误把 ``/data/kb-other`` 当成在 ``/data/kb`` 里面。
    # Windows 上两个路径如果位于不同盘符，commonpath() 会抛出 ValueError；
    # 这种情况显然不在同一个规定文件夹里，所以这里按检查失败处理。
    try:
        inside_root = os.path.commonpath([resolved_root, target_path]) == resolved_root
    except ValueError:
        inside_root = False

    # 第二层检查的是最终真实路径。目标也不能刚好等于 root，否则后续代码可能
    # 把整个 uploads 文件夹误当成一个上传文件来操作。
    if not inside_root or target_path == resolved_root:
        raise PathValidationError(f"invalid {field_name}")

    return target_path
