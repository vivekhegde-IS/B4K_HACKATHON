from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rag.chunking import chunk_pages
from app.rag.document_loader import load_pdf
from app.rag.embeddings import LocalEmbeddingService
from app.rag.ingest import ingest
from app.rag.retriever import PolicyRetriever
from app.rag.vectorstore import PolicyVectorStore, VectorStoreError
from app.services.rag_service import RAGService


SERVICE_ROOT = Path(__file__).parents[1]
PDF_PATH = SERVICE_ROOT / "source" / "order_cancellation_return_policy.pdf"


@pytest.fixture(scope="module")
def indexed_store(tmp_path_factory):
    pages = load_pdf(PDF_PATH)
    chunks = chunk_pages(pages)
    store = PolicyVectorStore(tmp_path_factory.mktemp("chroma"))
    store.upsert(chunks)
    return store


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_pdf_pages_and_metadata():
    pages = load_pdf(PDF_PATH)
    assert len(pages) == 13
    assert pages[0].page == 1
    assert pages[0].source == "order_cancellation_return_policy.pdf"
    assert pages[0].document_type == "return_policy"


def test_chunking_preserves_metadata():
    chunks = chunk_pages(load_pdf(PDF_PATH))
    assert len(chunks) > 13
    assert all(chunk.text for chunk in chunks)
    assert all({"source", "page", "document_type"} <= chunk.metadata.keys() for chunk in chunks)
    assert all(chunk.metadata["policy_scope"] in {"standard", "hyperlocal"} for chunk in chunks)


def test_books_chunks_preserve_scope_and_category():
    chunks = chunk_pages(load_pdf(PDF_PATH))
    standard_books = [
        chunk for chunk in chunks
        if chunk.metadata["page"] == 3 and "Books (All books)" in chunk.text
    ]
    hyperlocal_books = [
        chunk for chunk in chunks
        if chunk.metadata["page"] == 11 and "Books (All books)" in chunk.text
    ]
    assert standard_books
    assert hyperlocal_books
    assert standard_books[0].metadata["category"] == "Books"
    assert standard_books[0].metadata["policy_scope"] == "standard"
    assert hyperlocal_books[0].metadata["category"] == "Books"
    assert hyperlocal_books[0].metadata["policy_scope"] == "hyperlocal"


def test_retrieval_preserves_policy_source(indexed_store):
    results = PolicyRetriever(indexed_store).retrieve("What is the return policy for books?")
    assert results
    assert any(result["metadata"]["page"] in {3, 4, 11} for result in results)
    assert all(result["metadata"]["source"] == "order_cancellation_return_policy.pdf" for result in results)


def test_api_policy_query(monkeypatch, indexed_store):
    service = RAGService()
    service._retriever = PolicyRetriever(indexed_store)
    monkeypatch.setattr("app.api.rag.service", service)
    response = TestClient(app).post(
        "/api/rag/query",
        json={"query": "What is the return policy for books?", "language": "en"},
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["intent"] == "policy_query"
    assert payload["sources"]


def test_unknown_question_is_not_hallucinated(monkeypatch, indexed_store):
    service = RAGService()
    service._retriever = PolicyRetriever(indexed_store)
    monkeypatch.setattr("app.api.rag.service", service)
    payload = TestClient(app).post(
        "/api/rag/query",
        json={"query": "What is the employee discount?", "language": "en"},
    ).json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "KNOWLEDGE_NOT_FOUND"
    assert "couldn't find" in payload["answer"]


def test_empty_store_is_controlled(tmp_path):
    service = RAGService()
    service._retriever = PolicyRetriever(PolicyVectorStore(tmp_path / "empty"))
    payload = service.query("What is the return policy?", "en").model_dump()
    assert payload["success"] is False
    assert payload["error"]["code"] == "KNOWLEDGE_BASE_EMPTY"


def test_embedding_failure_is_controlled(tmp_path):
    class BrokenEmbedding(LocalEmbeddingService):
        def embed_many(self, texts):
            raise ValueError("simulated embedding failure")

    store = PolicyVectorStore(tmp_path / "failure", embedding_service=BrokenEmbedding())
    with pytest.raises(VectorStoreError, match="could not be indexed"):
        store.upsert(chunk_pages(load_pdf(PDF_PATH))[:1])


def test_reindex_is_idempotent(tmp_path, monkeypatch):
    store = PolicyVectorStore(tmp_path / "repeat")
    chunks = chunk_pages(load_pdf(PDF_PATH))
    assert store.upsert(chunks) == len(chunks)
    assert store.upsert(chunks) == len(chunks)
    assert store.count() == len(chunks)


def test_response_accepts_supported_languages(monkeypatch, indexed_store):
    service = RAGService()
    service._retriever = PolicyRetriever(indexed_store)
    monkeypatch.setattr("app.api.rag.service", service)
    response = TestClient(app).post(
        "/api/rag/query",
        json={"query": "What is the return policy?", "language": "kn"},
    )
    assert response.status_code == 200
    assert response.json()["language"] == "kn"