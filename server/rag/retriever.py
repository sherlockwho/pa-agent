from __future__ import annotations

import math
import re
from collections import Counter

from server.config import RAGSettings
from server.models import RAGChunk, RAGSearchResult
from server.rag.indexer import DocumentIndexer


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_+-]+|[一-鿿]")


class DocumentRetriever:
    def __init__(self, indexer: DocumentIndexer, settings: RAGSettings):
        self.indexer = indexer
        self.settings = settings

    def search(self, query: str, top_k: int | None = None) -> list[RAGSearchResult]:
        limit = top_k or self.settings.top_k
        if self.indexer.embedder.available:
            return self._faiss_search(query, limit)
        return self._keyword_search(query, limit)

    def _faiss_search(self, query: str, top_k: int) -> list[RAGSearchResult]:
        try:
            import faiss

            chunks = self.indexer.load_chunks()
            if not chunks:
                return []

            if not self.indexer.faiss_index_path.exists():
                self.indexer._rebuild_faiss(chunks)
                if not self.indexer.faiss_index_path.exists():
                    return self._keyword_search(query, top_k)

            index = faiss.read_index(str(self.indexer.faiss_index_path))
            query_vec = self.indexer.embedder.encode_single(query).reshape(1, -1)
            k = min(top_k, len(chunks))
            scores, ids = index.search(query_vec, k)

            results: list[RAGSearchResult] = []
            for score, idx in zip(scores[0], ids[0]):
                if idx < 0 or idx >= len(chunks):
                    continue
                results.append(RAGSearchResult(chunk=chunks[idx], score=float(score)))
            return results
        except Exception:
            return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int) -> list[RAGSearchResult]:
        query_vector = self._vectorize(query)
        if not query_vector:
            return []
        results: list[RAGSearchResult] = []
        for chunk in self.indexer.load_chunks():
            score = self._cosine(query_vector, self._vectorize(chunk.text))
            if score > 0:
                results.append(RAGSearchResult(chunk=chunk, score=score))
        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]

    def _vectorize(self, text: str) -> Counter[str]:
        tokens = [token.lower() for token in TOKEN_PATTERN.findall(text)]
        return Counter(tokens)

    def _cosine(self, left: Counter[str], right: Counter[str]) -> float:
        common = set(left) & set(right)
        numerator = sum(left[token] * right[token] for token in common)
        left_norm = math.sqrt(sum(v * v for v in left.values()))
        right_norm = math.sqrt(sum(v * v for v in right.values()))
        if not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)
