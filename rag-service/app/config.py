from pathlib import Path
import os


SERVICE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(os.getenv("RAG_SOURCE_DIR", SERVICE_ROOT / "source"))
PDF_PATH = Path(
	os.getenv(
		"RAG_POLICY_PDF",
		SOURCE_DIR / "order_cancellation_return_policy.pdf",
	)
)
CHROMA_PERSIST_DIRECTORY = Path(
	os.getenv("CHROMA_PERSIST_DIRECTORY", SERVICE_ROOT / "chroma_db")
)
COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", "retailmate_policy")
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1200"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))
TOP_K = int(os.getenv("RAG_TOP_K", "5"))
NORMALIZED_POLICY_PATH = Path(
	os.getenv(
		"RAG_NORMALIZED_POLICY",
		SERVICE_ROOT.parent / "backend" / "data" / "policy" / "retailmate_policy.json",
	)
)