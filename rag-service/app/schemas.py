from typing import Literal

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    language: Literal["en", "hi", "kn"] = "en"


class SourceMetadata(BaseModel):
    source: str
    page: int
    category: str | None = None
    policy_scope: Literal["standard", "hyperlocal"] | None = None
    document_type: str | None = None


class RetrievedChunk(BaseModel):
    text: str
    metadata: SourceMetadata
    distance: float | None = None


class RAGQueryResponse(BaseModel):
    success: bool
    answer: str | None = None
    intent: str | None = None
    language: str | None = None
    sources: list[SourceMetadata] = Field(default_factory=list)
    context: list[RetrievedChunk] = Field(default_factory=list)
    error: dict[str, str] | None = None