# RetailMate RAG Service

The RAG service provides grounded policy knowledge for the Agent. It is not the authority for inventory, orders, customers, returns, exchanges, or eligibility decisions.

## Flow

`order_cancellation_return_policy.pdf` is loaded page by page, split into bounded policy chunks, embedded with a deterministic local CPU vectorizer, and upserted into persistent ChromaDB. Queries retrieve indexed excerpts and preserve source/page metadata for the downstream Agent.

The source PDF is stored at `rag-service/source/order_cancellation_return_policy.pdf`. Backend's normalized policy JSON is used only to improve optional category metadata; the PDF remains the primary grounding source.

## Setup

```powershell
cd rag-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Index or re-index idempotently with:

```powershell
python -m app.rag.ingest
```

Start the service with:

```powershell
python -m uvicorn app.main:app --reload --port 8001
```

Chroma data is persisted in `rag-service/chroma_db`, which is ignored by Git. The service does not ingest on startup or on each query.

## API

`POST /api/rag/query`

```json
{
	"query": "What is the return policy for books?",
	"language": "en"
}
```

Successful responses contain `success`, `answer`, `intent`, `language`, `sources`, and retrieved `context`. Each source includes the actual PDF filename and page, plus category/document type when confidently available.

An empty store returns `KNOWLEDGE_BASE_EMPTY`; unsupported questions return `KNOWLEDGE_NOT_FOUND`. Errors are structured and never expose Python traces. Hindi and Kannada language values are accepted and preserved; localized generation remains the Agent/LLM integration responsibility.

## Limitations

The initial implementation deliberately has no LLM call, translation provider, exchange-rule generator, or transactional mutation. Answers are retrieved policy excerpts so the caller can apply deterministic business rules and optionally localize them.