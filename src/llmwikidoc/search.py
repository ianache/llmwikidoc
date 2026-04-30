"""Hybrid search — BM25 + vector embeddings + graph traversal, fused with RRF."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from llmwikidoc.config import Config
from llmwikidoc.graph import KnowledgeGraph
from llmwikidoc.wiki import WikiManager, WikiPage


@dataclass
class SearchResult:
    page: WikiPage
    score: float
    sources: list[str] = field(default_factory=list)  # which streams matched: bm25, vector, graph


# ── Embeddings cache ──────────────────────────────────────────────────────────

class EmbeddingCache:
    """Persist embeddings keyed by content hash to avoid redundant API calls."""

    def __init__(self, cache_path: Path) -> None:
        self.path = cache_path
        self._cache: dict[str, list[float]] = {}
        if cache_path.exists():
            self._cache = json.loads(cache_path.read_text(encoding="utf-8"))

    def get(self, text: str) -> list[float] | None:
        return self._cache.get(_content_hash(text))

    def set(self, text: str, vector: list[float]) -> None:
        self._cache[_content_hash(text)] = vector

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._cache), encoding="utf-8")


# ── HybridSearch ─────────────────────────────────────────────────────────────

class HybridSearch:
    """
    Three-stream hybrid search with Reciprocal Rank Fusion.

    Streams:
      1. BM25       — keyword matching with stemming via rank-bm25
      2. Vector     — semantic similarity via Gemini embeddings
      3. Graph      — entity relationship traversal via KnowledgeGraph
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._wiki = WikiManager(config.wiki_path)
        self._graph = KnowledgeGraph(config.wiki_path / "graph.json")
        self._embed_cache = EmbeddingCache(config.wiki_path / ".embeddings" / "cache.json")
        self._pages: list[WikiPage] = []
        self._bm25: BM25Okapi | None = None
        self._corpus_texts: list[str] = []

    def build_index(self) -> None:
        """Load all wiki pages and build the BM25 index."""
        self._pages = self._wiki.all_pages()
        self._corpus_texts = [_page_text(p) for p in self._pages]
        tokenized = [_tokenize(t) for t in self._corpus_texts]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Run hybrid search and return top_k results ranked by RRF."""
        if not self._pages:
            self.build_index()

        bm25_ranks = self._bm25_search(query)
        vector_ranks = self._vector_search(query)
        graph_ranks = self._graph_search(query)

        fused = _reciprocal_rank_fusion(
            [bm25_ranks, vector_ranks, graph_ranks],
            weights=[
                self._config.search.bm25_weight,
                self._config.search.vector_weight,
                self._config.search.graph_weight,
            ],
        )

        results: list[SearchResult] = []
        for page_idx, score in sorted(fused.items(), key=lambda x: x[1], reverse=True)[:top_k]:
            sources: list[str] = []
            if page_idx in {i for i, _ in bm25_ranks}:
                sources.append("bm25")
            if page_idx in {i for i, _ in vector_ranks}:
                sources.append("vector")
            if page_idx in {i for i, _ in graph_ranks}:
                sources.append("graph")
            results.append(SearchResult(page=self._pages[page_idx], score=score, sources=sources))

        return results

    # ── BM25 stream ───────────────────────────────────────────────────────────

    def _bm25_search(self, query: str) -> list[tuple[int, float]]:
        if not self._bm25 or not self._pages:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [(i, s) for i, s in ranked if s > 0]

    # ── Vector stream ─────────────────────────────────────────────────────────

    def _vector_search(self, query: str) -> list[tuple[int, float]]:
        if not self._pages:
            return []

        try:
            from llmwikidoc.llm import LLMClient
            with LLMClient(self._config) as llm:
                query_vec = llm.embed(query)
                page_vecs: list[list[float]] = []
                cache_dirty = False
                for page_text in self._corpus_texts:
                    cached = self._embed_cache.get(page_text)
                    if cached is not None:
                        page_vecs.append(cached)
                    else:
                        vec = llm.embed(page_text[:2000])  # truncate for embedding
                        self._embed_cache.set(page_text, vec)
                        page_vecs.append(vec)
                        cache_dirty = True
                if cache_dirty:
                    self._embed_cache.save()
        except Exception:
            return []

        scores = [_cosine_similarity(query_vec, pv) for pv in page_vecs]
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [(i, s) for i, s in ranked if s > 0]

    # ── Graph stream ──────────────────────────────────────────────────────────

    def _graph_search(self, query: str) -> list[tuple[int, float]]:
        """Find pages whose entity appears in the knowledge graph near the query terms."""
        if not self._pages:
            return []

        # Find entity names in graph that match the query
        matching_entities = self._graph.search_entities(query)
        if not matching_entities:
            return []

        # Also include neighbors (1 hop)
        expanded: set[str] = set(matching_entities)
        for entity in matching_entities:
            expanded.update(self._graph.neighbors(entity))

        # Score pages by how many matching entities they mention
        results: list[tuple[int, float]] = []
        for idx, page in enumerate(self._pages):
            page_text_lower = _page_text(page).lower()
            hits = sum(1 for e in expanded if e.lower() in page_text_lower)
            if hits > 0:
                results.append((idx, float(hits)))

        return sorted(results, key=lambda x: x[1], reverse=True)


# ── Reciprocal Rank Fusion ────────────────────────────────────────────────────

def _reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[int, float]]],
    weights: list[float],
    k: int = 60,
) -> dict[int, float]:
    """
    Combine multiple ranked lists into a single score dict using weighted RRF.
    Score for item i = sum over lists of weight * 1/(k + rank).
    """
    scores: dict[int, float] = {}
    for ranked_list, weight in zip(ranked_lists, weights):
        for rank, (page_idx, _) in enumerate(ranked_list, start=1):
            scores[page_idx] = scores.get(page_idx, 0.0) + weight * (1.0 / (k + rank))
    return scores


# ── Utilities ─────────────────────────────────────────────────────────────────

def _page_text(page: WikiPage) -> str:
    """Combine page name and body for indexing."""
    name = page.frontmatter.get("name", page.path.stem)
    return f"{name}\n{page.body}"


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer, lowercased."""
    import re
    return re.findall(r"\w+", text.lower())


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text[:2000].encode()).hexdigest()[:16]
