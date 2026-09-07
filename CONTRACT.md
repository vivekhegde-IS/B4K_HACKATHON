# Initial API Contract

## Ownership

- Frontend owns the React UI and calls Agent for assistant interactions.
- Backend owns products, inventory, customers, orders, returns, and exchanges.
- RAG owns policy and knowledge retrieval.
- Agent owns assistant orchestration.
- Agent owns STT/TTS voice endpoints.

## Reserved endpoints

| Method | Path | Owner | Status |
| --- | --- | --- | --- |
| GET | `/health` | Each service | Implemented |
| POST | `/api/assistant/query` | Agent | Reserved |
| POST | `/api/voice/tts` | Agent | Reserved |

The initial `/health` response for every service is `{ "status": "ok" }`. Domain endpoints will be defined before feature implementation.