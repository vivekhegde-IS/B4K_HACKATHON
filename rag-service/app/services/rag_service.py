from ..schemas import RAGQueryResponse, RetrievedChunk, SourceMetadata
from ..rag.retriever import PolicyRetriever
from ..rag.vectorstore import PolicyVectorStore, VectorStoreError


KNOWLEDGE_BASE_EMPTY = "The knowledge base has not been indexed yet."
NOT_FOUND = "I couldn't find that information in the available knowledge base."


class RAGService:
    def __init__(self):
        self._retriever: PolicyRetriever | None = None

    def _get_retriever(self) -> PolicyRetriever:
        if self._retriever is None:
            self._retriever = PolicyRetriever(PolicyVectorStore())
        return self._retriever

    def query(self, question: str, language: str) -> RAGQueryResponse:
        try:
            retriever = self._get_retriever()
            if retriever.store.count() == 0:
                return RAGQueryResponse(
                    success=False,
                    language=language,
                    error={"code": "KNOWLEDGE_BASE_EMPTY", "message": KNOWLEDGE_BASE_EMPTY},
                )
            matches = retriever.retrieve(question)
        except VectorStoreError as exc:
            return RAGQueryResponse(
                success=False,
                language=language,
                error={"code": "RAG_RETRIEVAL_FAILED", "message": str(exc)},
            )
        except ValueError:
            return RAGQueryResponse(
                success=False,
                language=language,
                error={"code": "EMBEDDING_FAILED", "message": "The question could not be processed."},
            )

        if not matches:
            return RAGQueryResponse(
                success=False,
                language=language,
                answer=NOT_FOUND,
                error={"code": "KNOWLEDGE_NOT_FOUND", "message": NOT_FOUND},
            )

        context = [
            RetrievedChunk(
                text=match["text"],
                metadata=SourceMetadata(**match["metadata"]),
                distance=match.get("distance"),
            )
            for match in matches
        ]
        sources = []
        seen = set()
        for chunk in context:
            key = (chunk.metadata.source, chunk.metadata.page)
            if key not in seen:
                seen.add(key)
                sources.append(chunk.metadata)
        answer = "\n\n".join(chunk.text for chunk in context)
        return RAGQueryResponse(
            success=True,
            answer=answer,
            intent="policy_query",
            language=language,
            sources=sources,
            context=context,
        )