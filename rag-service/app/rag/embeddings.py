import hashlib
import math
import re


class LocalEmbeddingService:
    """Small deterministic CPU embedding suitable for local policy retrieval."""

    dimensions = 384
    _token_pattern = re.compile(r"[\w]+", re.UNICODE)

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = self._token_pattern.findall(text.casefold())
        if not tokens:
            raise ValueError("Cannot embed empty text")
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]