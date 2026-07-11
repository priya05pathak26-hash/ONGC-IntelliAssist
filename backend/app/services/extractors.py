from pathlib import Path

import fitz
from docx import Document as DocxDocument


def extract_text(path: Path) -> list[tuple[int | None, str]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        pages: list[tuple[int | None, str]] = []
        with fitz.open(path) as pdf:
            for index, page in enumerate(pdf, start=1):
                pages.append((index, page.get_text("text")))
        return pages
    if suffix == ".docx":
        doc = DocxDocument(path)
        text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
        return [(None, text)]
    if suffix == ".txt":
        return [(None, path.read_text(encoding="utf-8", errors="ignore"))]
    raise ValueError("Unsupported file format")

