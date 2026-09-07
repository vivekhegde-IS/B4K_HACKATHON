# Architecture

Frontend (:5173) calls Agent (:8003). Agent delegates to RAG (:8001) for knowledge and Backend (:8002) for transactional data. RAG persists retrieval data in ChromaDB; Backend persists authoritative data in SQLite.