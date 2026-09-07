from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


class DocumentLoadError(RuntimeError):
    """A policy document could not be read safely."""


@dataclass(frozen=True)
class PageDocument:
    text: str
    source: str
    page: int
    document_type: str = "return_policy"


def load_pdf(path: str | Path) -> list[PageDocument]:
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise DocumentLoadError(f"Policy document not found: {pdf_path.name}")

    try:
        reader = PdfReader(str(pdf_path))
        documents: list[PageDocument] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = " ".join((page.extract_text() or "").split())
            if text:
                documents.append(
                    PageDocument(
                        text=text,
                        source=pdf_path.name,
                        page=page_number,
                    )
                )
    except Exception as exc:
        raise DocumentLoadError("The policy document could not be read.") from exc

    if not documents:
        raise DocumentLoadError("The policy document contains no readable text.")
    return documents