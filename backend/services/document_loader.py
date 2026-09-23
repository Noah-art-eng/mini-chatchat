import csv
import os

from docx import Document

from rag import load_pdf


def load_text(file_path):
    """负责 load_text 的函数职责。"""
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def load_docx(file_path):
    """负责 load_docx 的函数职责。"""
    document = Document(file_path)
    paragraphs = [
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.text
    ]
    return "\n".join(paragraphs)


def load_csv(file_path):
    """负责 load_csv 的函数职责。"""
    rows = []

    with open(file_path, "r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file)

        for row in reader:
            rows.append(" | ".join(row))

    return "\n".join(rows)


def load_file(file_path):
    """负责 load_file 的函数职责。"""
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
