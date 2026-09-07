from ..config import PDF_PATH
from .chunking import chunk_pages
from .document_loader import load_pdf
from .vectorstore import PolicyVectorStore


def ingest() -> int:
    pages = load_pdf(PDF_PATH)
    chunks = chunk_pages(pages)
    store = PolicyVectorStore()
    return store.upsert(chunks)


if __name__ == "__main__":
    print(f"Indexed {ingest()} policy chunks from {PDF_PATH.name}")