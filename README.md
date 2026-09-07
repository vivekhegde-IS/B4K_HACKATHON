# RetailMate

RetailMate is a multilingual retail kiosk application for English, Hindi, and Kannada. This repository currently contains the initial runnable service skeleton only; business features are intentionally not implemented.

## Architecture

The React/Vite frontend uses the Agent service as the assistant entry point. Agent delegates knowledge and policy questions to RAG and live transactional questions to Backend. Backend is the authoritative source for transactional data, while ChromaDB is the retrieval store. The LLM must never modify SQLite directly.

## Services and ports

| Service | Responsibility | Port |
| --- | --- | ---: |
| Frontend | React kiosk UI | 5173 |
| RAG | Knowledge retrieval | 8001 |
| Backend | Transactional data | 8002 |
| Agent | Assistant orchestration and voice | 8003 |

## Local setup

1. Copy `.env.example` to `.env` and adjust values as needed.
2. Start each Python service from its directory:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8002
   ```

   Use ports `8001` and `8003` for RAG and Agent respectively.
3. Start the frontend:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

4. The frontend is available at http://localhost:5173.

Docker Compose provides a documented skeleton for the same four services. It is not yet a production deployment configuration.

## Environment variables

See `.env.example` for service URLs, SQLite, ChromaDB, OpenRouter, STT, and TTS settings. Never commit `.env` or credentials.

## Team and branches

`main` is the integration branch. Developers work on assigned branches and merge through pull requests:

- `member-1/frontend-integration`
- `member-2/backend`
- `member-3/rag`
- `member-4/agent-voice`

See `TEAM_STATUS.md` and `CONTRACT.md` for ownership and initial contracts.

## Repository

The configured remote is https://github.com/vivekhegde-IS/B4K_HACKATHON.git.