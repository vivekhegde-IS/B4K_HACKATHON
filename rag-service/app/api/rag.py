from fastapi import APIRouter

from ..schemas import RAGQueryRequest, RAGQueryResponse
from ..services.rag_service import RAGService


router = APIRouter(prefix="/api/rag", tags=["RAG"])
service = RAGService()


@router.post("/query", response_model=RAGQueryResponse)
def query(request: RAGQueryRequest) -> RAGQueryResponse:
	return service.query(request.query, request.language)