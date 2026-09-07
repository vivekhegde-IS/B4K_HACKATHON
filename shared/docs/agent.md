# Agent

Agent owns assistant orchestration and the `POST /api/assistant/query` contract. It may call Backend and RAG, but the LLM never writes to SQLite.