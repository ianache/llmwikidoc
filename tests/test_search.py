"""Tests for search.py — BM25, RRF, graph stream, embedding cache."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from llmwikidoc.config import Config, SearchConfig
from llmwikidoc.search import (
    HybridSearch,
    EmbeddingCache,
    _reciprocal_rank_fusion,
    _cosine_similarity,
    _tokenize,
    _content_hash,
)
from llmwikidoc.wiki import WikiManager


def make_wiki_with_pages(wiki_path: Path) -> WikiManager:
    wiki = WikiManager(wiki_path)
    wiki.create_or_update_page(
        "entities", "UserService",
        "# UserService\n\nHandles authentication and user sessions.",
        page_type="class", sources=["sha1"],
    )
    wiki.create_or_update_page(
        "entities", "PaymentGateway",
        "# PaymentGateway\n\nProcesses credit card payments via Stripe.",
        page_type="class", sources=["sha2"],
    )
    wiki.create_or_update_page(
        "concepts", "Authentication",
        "# Authentication\n\nJWT-based auth flow used by UserService.",
        page_type="concept", sources=["sha1"],
    )
    return wiki


# ── Unit tests ────────────────────────────────────────────────────────────────

def test_tokenize():
    tokens = _tokenize("Hello, World! This is a test.")
    assert "hello" in tokens
    assert "world" in tokens
    assert "test" in tokens


def test_cosine_similarity_identical():
    v = [1.0, 0.0, 0.0]
    assert abs(_cosine_similarity(v, v) - 1.0) < 1e-9


def test_cosine_similarity_orthogonal():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(_cosine_similarity(a, b)) < 1e-9


def test_cosine_similarity_zero_vector():
    assert _cosine_similarity([], []) == 0.0
    assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_reciprocal_rank_fusion_single_list():
    ranked = [(0, 1.0), (1, 0.8), (2, 0.5)]
    result = _reciprocal_rank_fusion([ranked], weights=[1.0])
    # Item 0 should score highest
    assert result[0] > result[1] > result[2]


def test_reciprocal_rank_fusion_combines_lists():
    list1 = [(0, 1.0), (1, 0.5)]
    list2 = [(1, 1.0), (0, 0.3)]
    result = _reciprocal_rank_fusion([list1, list2], weights=[0.5, 0.5])
    # Both 0 and 1 appear in both lists, scores should be close
    assert 0 in result
    assert 1 in result


def test_reciprocal_rank_fusion_weights_matter():
    ranked = [(0, 1.0), (1, 0.5)]
    high_weight = _reciprocal_rank_fusion([ranked], weights=[2.0])
    low_weight = _reciprocal_rank_fusion([ranked], weights=[0.5])
    assert high_weight[0] > low_weight[0]


def test_content_hash_deterministic():
    h1 = _content_hash("same text")
    h2 = _content_hash("same text")
    assert h1 == h2


def test_content_hash_different_texts():
    assert _content_hash("text a") != _content_hash("text b")


# ── EmbeddingCache ────────────────────────────────────────────────────────────

def test_embedding_cache_miss_returns_none(tmp_path):
    cache = EmbeddingCache(tmp_path / "cache.json")
    assert cache.get("unknown text") is None


def test_embedding_cache_set_and_get(tmp_path):
    cache = EmbeddingCache(tmp_path / "cache.json")
    cache.set("hello", [0.1, 0.2, 0.3])
    assert cache.get("hello") == [0.1, 0.2, 0.3]


def test_embedding_cache_persists(tmp_path):
    path = tmp_path / "cache.json"
    cache = EmbeddingCache(path)
    cache.set("hello", [1.0, 2.0])
    cache.save()

    cache2 = EmbeddingCache(path)
    assert cache2.get("hello") == [1.0, 2.0]


# ── BM25 stream ───────────────────────────────────────────────────────────────

def test_bm25_finds_relevant_page(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)
    make_wiki_with_pages(config.wiki_path)

    searcher = HybridSearch(config)
    searcher.build_index()

    results = searcher._bm25_search("authentication user")
    assert len(results) > 0
    # The UserService / Authentication pages should rank higher than PaymentGateway
    top_indices = [i for i, _ in results[:2]]
    top_pages = [searcher._pages[i].path.stem for i in top_indices]
    assert any("user" in name.lower() or "auth" in name.lower() for name in top_pages)


def test_bm25_no_results_for_unrelated_query(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)
    make_wiki_with_pages(config.wiki_path)

    searcher = HybridSearch(config)
    searcher.build_index()

    results = searcher._bm25_search("xyzzy_nonexistent_term")
    assert results == []


# ── Graph stream ──────────────────────────────────────────────────────────────

def test_graph_stream_finds_related_pages(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)
    make_wiki_with_pages(config.wiki_path)

    from llmwikidoc.graph import KnowledgeGraph
    graph = KnowledgeGraph(config.wiki_path / "graph.json")
    graph.add_entity("UserService", "class")
    graph.add_relation("UserService", "Authentication", "implements")
    graph.save()

    searcher = HybridSearch(config)
    searcher.build_index()

    results = searcher._graph_search("UserService")
    assert len(results) > 0


def test_graph_stream_empty_when_no_graph(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)
    make_wiki_with_pages(config.wiki_path)

    searcher = HybridSearch(config)
    searcher.build_index()

    results = searcher._graph_search("UserService")
    # No graph exists yet, should return empty or find by name matching
    assert isinstance(results, list)


# ── HybridSearch.search ───────────────────────────────────────────────────────

@patch("llmwikidoc.search.HybridSearch._vector_search")
def test_hybrid_search_returns_results(mock_vector, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_vector.return_value = []  # skip vector to avoid API calls

    config = Config(project_root=tmp_path)
    make_wiki_with_pages(config.wiki_path)

    searcher = HybridSearch(config)
    results = searcher.search("authentication", top_k=3)

    assert len(results) > 0
    assert all(hasattr(r, "page") for r in results)
    assert all(hasattr(r, "score") for r in results)
    assert results == sorted(results, key=lambda r: r.score, reverse=True)


@patch("llmwikidoc.search.HybridSearch._vector_search")
def test_hybrid_search_top_k_respected(mock_vector, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_vector.return_value = []

    config = Config(project_root=tmp_path)
    make_wiki_with_pages(config.wiki_path)

    searcher = HybridSearch(config)
    results = searcher.search("service", top_k=2)
    assert len(results) <= 2


@patch("llmwikidoc.search.HybridSearch._vector_search")
def test_hybrid_search_empty_wiki(mock_vector, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_vector.return_value = []

    config = Config(project_root=tmp_path)
    # Don't create any pages
    from llmwikidoc.wiki import WikiManager
    WikiManager(config.wiki_path)  # just create dirs

    searcher = HybridSearch(config)
    results = searcher.search("anything")
    assert results == []
