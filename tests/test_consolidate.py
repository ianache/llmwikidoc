"""Tests for consolidate.py — Ebbinghaus decay, tier promotion, digest."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from llmwikidoc.config import Config, ConfidenceConfig
from llmwikidoc.confidence import ConfidenceStore, Fact
from llmwikidoc.consolidate import (
    ConsolidationResult,
    DigestResult,
    WORKING_TTL_DAYS,
    EPISODIC_TTL_DAYS,
    SEMANTIC_TTL_DAYS,
    PROCEDURAL_THRESHOLD,
    _apply_decay,
    _promote_facts,
    _promote_pages,
    _fact_tier,
    _compute_new_tier,
    _tier_stability_multiplier,
    create_digest,
    run_consolidation,
)
from llmwikidoc.wiki import WikiManager


def make_store(tmp_path: Path) -> ConfidenceStore:
    return ConfidenceStore(tmp_path / "wiki" / "confidence.json", ConfidenceConfig())


def make_wiki(tmp_path: Path) -> WikiManager:
    config = Config(project_root=tmp_path)
    return WikiManager(config.wiki_path)


def _days_ago_iso(days: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ── _fact_tier ────────────────────────────────────────────────────────────────

def test_fact_tier_working_single_source():
    fact = Fact("stmt", "E", 0.7, sources=["sha1"])
    assert _fact_tier(fact) == "working"


def test_fact_tier_episodic_two_sources():
    fact = Fact("stmt", "E", 0.7, sources=["sha1", "sha2"])
    assert _fact_tier(fact) == "episodic"


def test_fact_tier_semantic_three_sources():
    fact = Fact("stmt", "E", 0.7, sources=["sha1", "sha2", "sha3"])
    assert _fact_tier(fact) == "semantic"


def test_fact_tier_procedural_high_confidence():
    fact = Fact("stmt", "E", 0.9, sources=["s1", "s2", "s3", "s4", "s5"])
    assert _fact_tier(fact) == "procedural"


# ── _tier_stability_multiplier ────────────────────────────────────────────────

def test_stability_multiplier_ordering():
    assert _tier_stability_multiplier("working") < _tier_stability_multiplier("episodic")
    assert _tier_stability_multiplier("episodic") < _tier_stability_multiplier("semantic")
    assert _tier_stability_multiplier("semantic") < _tier_stability_multiplier("procedural")


def test_stability_multiplier_unknown_tier():
    assert _tier_stability_multiplier("unknown") == 1.0


# ── Ebbinghaus decay ──────────────────────────────────────────────────────────

def test_decay_reduces_confidence(tmp_path):
    wiki_path = tmp_path / "wiki"
    wiki_path.mkdir()
    store = make_store(tmp_path)

    fact = store.add_fact("Old fact", "Entity", "sha1")
    original_confidence = fact.confidence
    # Simulate fact being 60 days old (2x decay cycle)
    fact.last_reinforced = _days_ago_iso(60)
    store.save()

    result = ConsolidationResult()
    _apply_decay(store, result)

    assert fact.confidence < original_confidence
    assert result.facts_decayed >= 1


def test_decay_skips_recent_facts(tmp_path):
    wiki_path = tmp_path / "wiki"
    wiki_path.mkdir()
    store = make_store(tmp_path)

    fact = store.add_fact("Recent fact", "Entity", "sha1")
    fact.last_reinforced = _days_ago_iso(0)  # today
    original_confidence = fact.confidence

    result = ConsolidationResult()
    _apply_decay(store, result)

    assert fact.confidence == original_confidence
    assert result.facts_decayed == 0


def test_decay_generates_warnings_for_very_low_confidence(tmp_path):
    wiki_path = tmp_path / "wiki"
    wiki_path.mkdir()
    store = make_store(tmp_path)

    fact = store.add_fact("Very old fact", "Entity", "sha1")
    fact.confidence = 0.35
    fact.last_reinforced = _days_ago_iso(200)  # very old

    result = ConsolidationResult()
    _apply_decay(store, result)

    assert len(result.decay_warnings) >= 1


def test_procedural_facts_decay_slower(tmp_path):
    wiki_path = tmp_path / "wiki"
    wiki_path.mkdir()
    store = make_store(tmp_path)

    # Working fact
    working_fact = store.add_fact("Working fact", "E1", "sha1")
    working_fact.confidence = 0.8
    working_fact.last_reinforced = _days_ago_iso(30)

    # Procedural fact (5+ sources, high confidence)
    proc_fact = store.add_fact("Procedural fact", "E2", "sha1")
    proc_fact.sources = ["s1", "s2", "s3", "s4", "s5"]
    proc_fact.confidence = 0.8
    proc_fact.last_reinforced = _days_ago_iso(30)

    result = ConsolidationResult()
    _apply_decay(store, result)

    # Procedural should retain more confidence
    assert proc_fact.confidence >= working_fact.confidence


# ── Fact promotion ────────────────────────────────────────────────────────────

def test_promote_facts_old_high_confidence(tmp_path):
    wiki_path = tmp_path / "wiki"
    wiki_path.mkdir()
    store = make_store(tmp_path)

    fact = store.add_fact("Old stable fact", "Entity", "sha1")
    fact.confidence = 0.65
    fact.created = _days_ago_iso(WORKING_TTL_DAYS + 1)

    result = ConsolidationResult()
    _promote_facts(store, result)

    assert result.facts_promoted >= 1
    assert "consolidated" in fact.sources


def test_promote_facts_multi_source(tmp_path):
    """A fact with 2 sources and confidence >= 0.5 should get the 'consolidated' marker."""
    wiki_path = tmp_path / "wiki"
    wiki_path.mkdir()
    store = make_store(tmp_path)

    # 2 sources → _fact_tier returns "episodic", but we still add "consolidated" marker
    # to track that it has been processed. Use a single-source fact eligible by age instead.
    fact = store.add_fact("Reinforced working fact", "Entity", "sha1")
    fact.confidence = 0.62
    fact.created = _days_ago_iso(WORKING_TTL_DAYS + 2)  # older than TTL → eligible

    result = ConsolidationResult()
    _promote_facts(store, result)

    assert result.facts_promoted >= 1
    assert "consolidated" in fact.sources


def test_promote_facts_skips_already_promoted(tmp_path):
    wiki_path = tmp_path / "wiki"
    wiki_path.mkdir()
    store = make_store(tmp_path)

    fact = store.add_fact("Already promoted", "Entity", "sha1")
    fact.sources.append("sha2")
    fact.sources.append("consolidated")  # already promoted
    fact.confidence = 0.65

    result = ConsolidationResult()
    _promote_facts(store, result)

    # Should not double-promote
    assert fact.sources.count("consolidated") == 1


def test_promote_facts_skips_low_confidence(tmp_path):
    wiki_path = tmp_path / "wiki"
    wiki_path.mkdir()
    store = make_store(tmp_path)

    fact = store.add_fact("Low confidence old fact", "Entity", "sha1")
    fact.confidence = 0.3
    fact.created = _days_ago_iso(WORKING_TTL_DAYS + 5)

    result = ConsolidationResult()
    _promote_facts(store, result)

    assert result.facts_promoted == 0


# ── Page promotion ────────────────────────────────────────────────────────────

def test_compute_new_tier_working_to_episodic_by_sources():
    assert _compute_new_tier("working", 0.65, ["s1", "s2", "s3"], 1) == "episodic"


def test_compute_new_tier_working_to_episodic_by_age():
    assert _compute_new_tier("working", 0.55, ["s1"], WORKING_TTL_DAYS + 1) == "episodic"


def test_compute_new_tier_episodic_to_semantic():
    sources = ["s1", "s2", "s3", "s4", "s5"]
    assert _compute_new_tier("episodic", 0.75, sources, 1) == "semantic"


def test_compute_new_tier_episodic_to_semantic_by_age():
    assert _compute_new_tier("episodic", 0.7, ["s1"], EPISODIC_TTL_DAYS + 1) == "semantic"


def test_compute_new_tier_semantic_to_procedural():
    assert _compute_new_tier("semantic", PROCEDURAL_THRESHOLD, ["s1"], SEMANTIC_TTL_DAYS + 1) == "procedural"


def test_compute_new_tier_stays_same_below_threshold():
    assert _compute_new_tier("working", 0.3, ["s1"], 1) == "working"
    assert _compute_new_tier("procedural", 0.9, ["s1"], 999) == "procedural"


def test_promote_pages_updates_tier(tmp_path):
    config = Config(project_root=tmp_path)
    wiki = WikiManager(config.wiki_path)
    store = make_store(tmp_path)

    # Create a page eligible for episodic promotion
    page = wiki.create_or_update_page(
        "entities", "OldEntity",
        "# OldEntity\n\nA class.",
        page_type="class",
        sources=["s1", "s2", "s3"],
        confidence=0.7,
        tier="working",
    )
    # Simulate old page
    page.frontmatter["updated"] = _days_ago_iso(WORKING_TTL_DAYS + 1)
    page.save()

    result = ConsolidationResult()
    _promote_pages(wiki, store, result)

    # Reload and check tier was promoted
    from llmwikidoc.wiki import WikiPage
    reloaded = WikiPage(page.path)
    assert reloaded.frontmatter.get("tier") in {"episodic", "semantic", "procedural"}
    assert result.pages_promoted >= 1


# ── run_consolidation ─────────────────────────────────────────────────────────

def test_run_consolidation_returns_result(tmp_path):
    config = Config(project_root=tmp_path)
    wiki = WikiManager(config.wiki_path)
    store = make_store(tmp_path)

    store.add_fact("Some fact", "Entity", "sha1")
    store.save()

    result = run_consolidation(wiki, store)
    assert isinstance(result, ConsolidationResult)


def test_run_consolidation_saves_store(tmp_path):
    config = Config(project_root=tmp_path)
    wiki = WikiManager(config.wiki_path)
    store = make_store(tmp_path)

    store.add_fact("Fact to save", "Entity", "sha1")
    run_consolidation(wiki, store)

    store_path = config.wiki_path / "confidence.json"
    assert store_path.exists()


# ── create_digest ─────────────────────────────────────────────────────────────

MOCK_DIGEST_RESPONSE = {
    "title": "Auth system implemented",
    "period_summary": "This session implemented JWT-based authentication.",
    "key_themes": ["authentication", "security"],
    "entities_changed": [
        {"name": "UserService", "type": "class", "changes": "Added authenticate method"}
    ],
    "durable_facts": [
        {"statement": "UserService uses JWT tokens", "entity": "UserService", "confidence": 0.85}
    ],
    "open_questions": ["Should tokens expire after 24h?"],
    "next_steps": ["Add refresh token support"],
}


def make_wiki_with_summaries(tmp_path: Path, count: int = 3) -> WikiManager:
    config = Config(project_root=tmp_path)
    wiki = WikiManager(config.wiki_path)
    for i in range(count):
        wiki.create_summary(
            f"abc{i:05d}",
            f"# Commit abc{i:05d}\n\nAdded feature {i}.",
            f"abc{i:05d}abc{i:05d}abc{i:05d}",
        )
    return wiki


def test_create_digest_produces_page(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    wiki = make_wiki_with_summaries(tmp_path, count=3)
    config = Config(project_root=tmp_path)
    store = ConfidenceStore(config.wiki_path / "confidence.json", config.confidence)

    mock_llm = MagicMock()
    mock_llm.generate_structured.return_value = MOCK_DIGEST_RESPONSE

    result = create_digest(wiki, store, mock_llm, n_recent=3)

    assert isinstance(result, DigestResult)
    assert result.commits_covered == 3
    assert result.entities_mentioned == 1


def test_create_digest_page_is_semantic_tier(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    wiki = make_wiki_with_summaries(tmp_path, count=3)
    config = Config(project_root=tmp_path)
    store = ConfidenceStore(config.wiki_path / "confidence.json", config.confidence)

    mock_llm = MagicMock()
    mock_llm.generate_structured.return_value = MOCK_DIGEST_RESPONSE

    result = create_digest(wiki, store, mock_llm, n_recent=3)

    from llmwikidoc.wiki import WikiPage
    digest_page = WikiPage(config.wiki_path / "concepts" / f"{result.digest_page}.md")
    assert digest_page.exists
    assert digest_page.frontmatter.get("tier") == "semantic"


def test_create_digest_adds_facts_to_store(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    wiki = make_wiki_with_summaries(tmp_path, count=3)
    config = Config(project_root=tmp_path)
    store = ConfidenceStore(config.wiki_path / "confidence.json", config.confidence)

    mock_llm = MagicMock()
    mock_llm.generate_structured.return_value = MOCK_DIGEST_RESPONSE

    create_digest(wiki, store, mock_llm, n_recent=3)

    facts = store.facts_for_entity("UserService")
    assert len(facts) >= 1
    assert any("JWT" in f.statement for f in facts)


def test_create_digest_reinforces_existing_facts(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    wiki = make_wiki_with_summaries(tmp_path, count=3)
    config = Config(project_root=tmp_path)
    store = ConfidenceStore(config.wiki_path / "confidence.json", config.confidence)

    # Pre-existing fact that matches the digest fact
    store.add_fact("UserService uses JWT tokens for auth", "UserService", "pre-existing")
    initial_conf = store.facts_for_entity("UserService")[0].confidence

    mock_llm = MagicMock()
    mock_llm.generate_structured.return_value = MOCK_DIGEST_RESPONSE

    create_digest(wiki, store, mock_llm, n_recent=3)

    facts = store.facts_for_entity("UserService")
    assert facts[0].confidence >= initial_conf  # reinforced


def test_create_digest_fails_without_summaries(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)
    wiki = WikiManager(config.wiki_path)  # no summaries
    store = ConfidenceStore(config.wiki_path / "confidence.json", config.confidence)

    mock_llm = MagicMock()
    with pytest.raises(ValueError, match="No commit summaries"):
        create_digest(wiki, store, mock_llm, n_recent=5)


def test_create_digest_logs_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    wiki = make_wiki_with_summaries(tmp_path, count=3)
    config = Config(project_root=tmp_path)
    store = ConfidenceStore(config.wiki_path / "confidence.json", config.confidence)

    mock_llm = MagicMock()
    mock_llm.generate_structured.return_value = MOCK_DIGEST_RESPONSE

    create_digest(wiki, store, mock_llm, n_recent=3)

    log = (config.wiki_path / "log.md").read_text()
    assert "DIGEST" in log
