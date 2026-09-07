from dataclasses import dataclass
import json
from pathlib import Path
import re

from ..config import CHUNK_OVERLAP, CHUNK_SIZE, NORMALIZED_POLICY_PATH
from .document_loader import PageDocument


@dataclass(frozen=True)
class PolicyChunk:
    text: str
    metadata: dict[str, str | int]
    chunk_index: int


def _known_categories(path: Path = NORMALIZED_POLICY_PATH) -> list[str]:
    if not path.is_file():
        return []
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
        categories = []
        for section in (policy.get("standard", {}), policy.get("hyperlocal", {})):
            categories.extend(item["name"] for item in section.get("categories", []))
        return categories
    except (OSError, json.JSONDecodeError, TypeError, KeyError):
        return []


def _category_for(text: str, categories: list[str]) -> str:
    lowered = text.casefold()
    matches = [category for category in categories if category.casefold() in lowered]
    return matches[0] if len(matches) == 1 else "general"


def chunk_pages(
    pages: list[PageDocument],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[PolicyChunk]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and overlap must be smaller")

    categories = _known_categories()
    chunks: list[PolicyChunk] = []
    for page in pages:
        start = 0
        page_index = 0
        while start < len(page.text):
            end = min(start + chunk_size, len(page.text))
            if end < len(page.text):
                boundary = max(page.text.rfind(".", start, end), page.text.rfind(";", start, end))
                if boundary > start + chunk_size // 2:
                    end = boundary + 1
            text = re.sub(r"\s+", " ", page.text[start:end]).strip()
            if text:
                chunks.append(
                    PolicyChunk(
                        text=text,
                        chunk_index=page_index,
                        metadata={
                            "source": page.source,
                            "page": page.page,
                            "category": _category_for(text, categories),
                            "document_type": page.document_type,
                        },
                    )
                )
                page_index += 1
            if end >= len(page.text):
                break
            start = max(end - overlap, start + 1)
    return chunks