import re

from ..config import TOP_K
from .vectorstore import PolicyVectorStore

STOPWORDS = {
    "a", "an", "and", "are", "for", "from", "how", "is", "it", "of", "on",
    "the", "to", "what", "when", "where", "which", "with", "this", "that",
}
GENERIC_POLICY_TERMS = {
    "action", "cancellation", "cancel", "customer", "days", "order", "policy",
    "product", "refund", "return", "returns", "window",
}


def _content_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\w]+", text.casefold())
        if token not in STOPWORDS and len(token) > 2
    }


class PolicyRetriever:
    def __init__(self, store: PolicyVectorStore | None = None):
        self.store = store or PolicyVectorStore()

    def retrieve(self, question: str, limit: int = TOP_K) -> list[dict]:
        vector_candidates = self.store.query(question, limit=max(limit * 10, 50))
        all_candidates = self.store.all_documents()
        candidates_by_text = {candidate["text"]: candidate for candidate in vector_candidates}
        candidates_by_text.update({candidate["text"]: candidate for candidate in all_candidates})
        candidates = list(candidates_by_text.values())
        query_tokens = _content_tokens(question)
        relevant = []
        for candidate in candidates:
            text_tokens = _content_tokens(candidate["text"])
            overlap = query_tokens & text_tokens
            if overlap:
                candidate["lexical_overlap"] = len(overlap)
                candidate["exact_match"] = sum(
                    1 for token in query_tokens if token in candidate["text"].casefold()
                )
                candidate["specific_match"] = sum(
                    1
                    for token in query_tokens - GENERIC_POLICY_TERMS
                    if token in candidate["text"].casefold()
                )
                relevant.append(candidate)
        relevant.sort(
            key=lambda item: (
                -item["specific_match"],
                -item["exact_match"],
                -item["lexical_overlap"],
                item["distance"] if item["distance"] is not None else 999,
            )
        )
        return relevant[:limit]