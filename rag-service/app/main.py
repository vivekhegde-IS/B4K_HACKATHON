from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.rag import router as rag_router

app = FastAPI(title="RetailMate RAG", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(rag_router)