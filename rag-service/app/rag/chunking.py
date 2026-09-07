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
    explicit_books = re.search(r"\b(Books)\s*\(\s*All\s+books\s*\)", text, re.IGNORECASE)
    if explicit_books:
        return explicit_books.group(1)
    matches = [category for category in categories if category.casefold() in lowered]
    return matches[0] if len(matches) == 1 else "general"


def _scope_sections(text: str, inherited_scope: str) -> tuple[list[tuple[str, str]], str]:
    markers = list(re.finditer(r"Return Policy\s*-\s*Hyperlocal", text, re.IGNORECASE))
    if not markers:
        return [(text, inherited_scope)], inherited_scope

    sections = []
    start = 0
    scope = inherited_scope
    for marker in markers:
        if marker.start() > start:
            sections.append((text[start:marker.start()], scope))
        start = marker.start()
        scope = "hyperlocal"
    if start < len(text):
        sections.append((text[start:], scope))
    return sections, scope


def chunk_pages(
    pages: list[PageDocument],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[PolicyChunk]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and overlap must be smaller")

    categories = _known_categories()
    chunks: list[PolicyChunk] = []
    policy_scope = "standard"
    for page in pages:
        page_index = 0
        sections, policy_scope = _scope_sections(page.text, policy_scope)
        for section_text, section_scope in sections:
            start = 0
            while start < len(section_text):
                end = min(start + chunk_size, len(section_text))
                if end < len(section_text):
                    boundary = max(
                        section_text.rfind(".", start, end),
                        section_text.rfind(";", start, end),
                    )
                    if boundary > start + chunk_size // 2:
                        end = boundary + 1
                text = re.sub(r"\s+", " ", section_text[start:end]).strip()
                if text:
                    chunks.append(
                        PolicyChunk(
                            text=text,
                            chunk_index=page_index,
                            metadata={
                                "source": page.source,
                                "page": page.page,
                                "category": _category_for(text, categories),
                                "policy_scope": section_scope,
                                "document_type": page.document_type,
                            },
                        )
                    )
                    page_index += 1
                if end >= len(section_text):
                    break
                start = max(end - overlap, start + 1)
    return chunks