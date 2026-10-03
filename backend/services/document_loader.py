import csv
import os
import tempfile

from docx import Document
from pypdf import PdfReader

from rag import load_pdf


TEXT_PARSE_CHUNK_CHARS = 64 * 1024


def parse_file_to_text_file(
    source_path: str,
    destination_path: str,
    *,
    chunk_chars: int = TEXT_PARSE_CHUNK_CHARS,
) -> None:
    """把支持的文档解析到目标文本文件，避免额外构造完整正文字符串。

    TXT/MD 按字符分块读取，CSV 按行处理，PDF 按页提取，DOCX 按段落写入。
    PDF reader 和 python-docx 仍可能在内部保留文档结构；这里减少的是解析结果
    再额外形成完整 list/string 的内存，而不是宣称所有格式都能恒定内存解析。

    ``chunk_chars`` 控制每次从源文件读取的字符数，不是文件大小限制。解析先在
    destination 同目录写完 staging 文件，成功后再整体替换正式文件，因此中途
    失败不会留下半个结果，也不会提前破坏已有 destination。
    """
    source_path = os.fspath(source_path)
    destination_path = os.path.abspath(os.fspath(destination_path))
    extension = os.path.splitext(source_path)[1].lower()

    if extension not in {".txt", ".md", ".csv", ".pdf", ".docx"}:
        raise ValueError(
            f"Path-to-path parsing is unsupported for file type: {extension}"
        )

    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be greater than zero")

    destination_directory = os.path.dirname(destination_path)
    os.makedirs(destination_directory, exist_ok=True)
    # 只记录本次解析创建的 staging，异常时不会误删已有 destination。
    staging_path = None

    try:
        # staging 必须和 destination 同目录，才能让最后的 os.replace() 保持为
        # 同一文件系统内的切换，而不是再复制一次完整解析结果。
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination_directory,
            prefix=".mini_chatchat_parse_",
            suffix=".txt",
            delete=False,
        ) as staging_file:
            staging_path = staging_file.name

            if extension in {".txt", ".md"}:
                # 文本模式会处理跨读取边界的 UTF-8 字符；每次只读取 chunk_chars，
                # 不会因为中文或 emoji 跨底层 byte 边界而解码失败。
                with open(source_path, "r", encoding="utf-8") as source_file:
                    while True:
                        text_chunk = source_file.read(chunk_chars)
                        if not text_chunk:
                            break
                        staging_file.write(text_chunk)
            elif extension == ".csv":
                # 逐行写入时只在行与行之间添加换行，保持旧 join() 实现没有
                # trailing newline 的输出语义。
                with open(
                    source_path,
                    "r",
                    encoding="utf-8",
                    newline="",
                ) as source_file:
                    is_first_row = True
                    for row in csv.reader(source_file):
                        if not is_first_row:
                            staging_file.write("\n")
                        staging_file.write(" | ".join(row))
                        is_first_row = False
            elif extension == ".pdf":
                # 保持 rag.load_pdf() 的既有语义：忽略空页，每个有效页文本后
                # 都追加换行，包括最后一个有效页。
                reader = PdfReader(source_path)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        staging_file.write(page_text)
                        staging_file.write("\n")
            else:
                # python-docx 会加载文档结构，但直接写段落可避免再创建完整
                # paragraphs 文本列表和最终拼接字符串。
                document = Document(source_path)
                is_first_paragraph = True
                for paragraph in document.paragraphs:
                    if not paragraph.text:
                        continue
                    if not is_first_paragraph:
                        staging_file.write("\n")
                    staging_file.write(paragraph.text)
                    is_first_paragraph = False

        # staging 完整写入并关闭后才切换正式文件。解析失败时旧 destination
        # 始终未被打开或截断，成功时也不会出现只写了一部分的正式文件。
        os.replace(staging_path, destination_path)
        staging_path = None
    except Exception:
        if staging_path is not None:
            try:
                os.remove(staging_path)
            except OSError:
                # 清理失败不能盖掉真正的解析或替换错误，下面的 bare raise
                # 会继续抛出进入当前 except 时的原始异常。
                pass
        raise


def load_text(file_path):
    """兼容旧调用：一次性读取 TXT/MD；生产上传使用 path-to-path 分块解析。"""
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def load_docx(file_path):
    """兼容旧调用：提取非空段落并按换行拼接，保持历史输出格式。"""
    document = Document(file_path)
    paragraphs = [
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.text
    ]
    return "\n".join(paragraphs)


def load_csv(file_path):
    """兼容旧调用：按 csv.reader 解析并用竖线连接每行字段。"""
    rows = []

    with open(file_path, "r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file)

        for row in reader:
            rows.append(" | ".join(row))

    return "\n".join(rows)


def load_file(file_path):
    """兼容旧入口：按扩展名选择解析器并返回完整文本；生产流程不再使用它。"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext in [".txt", ".md"]:
        return load_text(file_path)

    if ext == ".pdf":
        return load_pdf(file_path)

    if ext == ".docx":
        return load_docx(file_path)

    if ext == ".csv":
        return load_csv(file_path)

    raise ValueError(f"Unsupported file type: {ext}")
