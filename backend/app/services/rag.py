from pathlib import Path
from typing import Iterable

from ..config import DOCS_DIR


class RagStore:
    def __init__(self) -> None:
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        self.documents = self._load_documents()

    def _load_documents(self) -> list[str]:
        docs: list[str] = []
        for path in DOCS_DIR.glob("*.txt"):
            docs.extend(chunk_text(path.read_text(encoding="utf-8", errors="ignore")))
        return docs

    def refresh(self) -> int:
        self.documents = self._load_documents()
        return len(self.documents)

    def retrieve(self, query: str, limit: int = 3) -> list[str]:
        if not query.strip() or not self.documents:
            return []
        query_terms = set(query.lower().split())
        scored = []
        for doc in self.documents:
            score = len(query_terms.intersection(doc.lower().split()))
            if score:
                scored.append((score, doc))
        scored.sort(reverse=True, key=lambda item: item[0])
        return [doc for _, doc in scored[:limit]]

    def add_document(self, name: str, text: str) -> Path:
        safe_name = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_")).strip() or "document"
        path = DOCS_DIR / f"{safe_name}.txt"
        path.write_text(text, encoding="utf-8")
        self.refresh()
        return path


def chunk_text(text: str, size: int = 900) -> Iterable[str]:
    paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
    buffer = ""
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) > size and buffer:
            yield buffer
            buffer = ""
        buffer = f"{buffer}\n{paragraph}".strip()
    if buffer:
        yield buffer
