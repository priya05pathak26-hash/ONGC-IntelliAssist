from pathlib import Path

import fitz
from docx import Document as DocxDocument


def extract_text(path: Path) -> list[tuple[int, str]]:
    """
    Extract text from every page.

    Returns a list of (page_number:int, text:str) tuples.
    page_number is ALWAYS 1-based (never None).  PDFs get real  For DOCX/TXT (which
    are single-page artefacts) a page_number of 1.
    """
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        pages: list[tuple[int, str]] = []
        with fitz.open(path) as pdf:
            for index, page in enumerate(pdf, start=1):
                pages.append((index, page.get_text("text")))
        return pages
    if suffix == ".docx":
        doc = DocxDocument(path)
        text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
        return [(1, text)]
    if suffix == ".txt":
        return [(1, path.read_text(encoding="utf-8", errors="ignore"))]
    raise ValueError("Unsupported file format")


