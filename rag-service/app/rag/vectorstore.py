from pathlib import Path

import chromadb

from ..config import CHROMA_PERSIST_DIRECTORY, COLLECTION_NAME
from .embeddings import LocalEmbeddingService
from .chunking import PolicyChunk


class VectorStoreError(RuntimeError):
    """A vector store operation failed safely."""


class PolicyVectorStore:
    def __init__(
        self,
        persist_directory: str | Path = CHROMA_PERSIST_DIRECTORY,
        embedding_service: LocalEmbeddingService | None = None,
    ):
        self.embedding_service = embedding_service or LocalEmbeddingService()
        try:
            Path(persist_directory).mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(persist_directory))
            self.collection = self.client.get_or_create_collection(COLLECTION_NAME)
        except Exception as exc:
            raise VectorStoreError("The knowledge base is unavailable.") from exc

    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception as exc:
            raise VectorStoreError("The knowledge base is unavailable.") from exc

    def upsert(self, chunks: list[PolicyChunk]) -> int:
        if not chunks:
            return 0
        try:
            documents = [chunk.text for chunk in chunks]
            ids = [
                f"{chunk.metadata['source']}:{chunk.metadata['page']}:{chunk.chunk_index}"
                for chunk in chunks
            ]
            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=self.embedding_service.embed_many(documents),
                metadatas=chunks_metadata(chunks),
            )
            return len(chunks)
        except Exception as exc:
            raise VectorStoreError("The knowledge base could not be indexed.") from exc

    def query(self, question: str, limit: int = 5) -> list[dict]:
        try:
            result = self.collection.query(
                query_embeddings=[self.embedding_service.embed(question)],
                n_results=limit,
                include=["documents", "metadatas", "distances"],
            )
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]
            return [
                {"text": text, "metadata": metadata, "distance": distance}
                for text, metadata, distance in zip(documents, metadatas, distances)
            ]
        except Exception as exc:
            raise VectorStoreError("Unable to retrieve from the knowledge base.") from exc

    def all_documents(self) -> list[dict]:
        try:
            result = self.collection.get(include=["documents", "metadatas"])
            return [
                {"text": text, "metadata": metadata, "distance": None}
                for text, metadata in zip(
                    result.get("documents", []), result.get("metadatas", [])
                )
            ]
        except Exception as exc:
            raise VectorStoreError("Unable to retrieve from the knowledge base.") from exc


def chunks_metadata(chunks: list[PolicyChunk]) -> list[dict[str, str | int]]:
    return [chunk.metadata for chunk in chunks]