"""Tests for confidence.py."""

from pathlib import Path
from llmwikidoc.confidence import ConfidenceStore, Fact, _fact_key
from llmwikidoc.config import ConfidenceConfig


def make_store(tmp_path: Path) -> ConfidenceStore:
    return ConfidenceStore(tmp_path / "confidence.json", ConfidenceConfig())


def test_add_fact(tmp_path):
    store = make_store(tmp_path)
    fact = store.add_fact("UserService handles auth", "UserService", "sha1")
    assert fact.confidence == 0.7
    assert fact.entity == "UserService"
    assert "sha1" in fact.sources


def test_reinforce_increases_confidence(tmp_path):
    store = make_store(tmp_path)
    store.add_fact("UserService handles auth", "UserService", "sha1")
    reinforced = store.reinforce("UserService", "UserService handles auth", "sha2")
    assert reinforced.confidence > 0.7
    assert "sha2" in reinforced.sources


def test_reinforce_caps_at_1(tmp_path):
    store = make_store(tmp_path)
    store.add_fact("X", "E", "s1")
    for i in range(20):
        store.reinforce("E", "X", f"s{i}")
    facts = store.facts_for_entity("E")
    assert facts[0].confidence <= 1.0


def test_contradict_decreases_confidence(tmp_path):
    store = make_store(tmp_path)
    store.add_fact("UserService uses Redis", "UserService", "sha1")
    store.contradict("UserService", "UserService uses Redis", "UserService uses Memcached")
    facts = store.facts_for_entity("UserService")
    assert facts[0].confidence < 0.7
    assert "UserService uses Memcached" in facts[0].contradicted_by


def test_contradict_floors_at_0(tmp_path):
    store = make_store(tmp_path)
    store.add_fact("X", "E", "s1")
    for _ in range(20):
        store.contradict("E", "X", "opposite")
    facts = store.facts_for_entity("E")
    assert facts[0].confidence >= 0.0


def test_persist_and_reload(tmp_path):
    path = tmp_path / "confidence.json"
    store = ConfidenceStore(path, ConfidenceConfig())
    store.add_fact("Foo uses bar", "Foo", "sha1")
    store.save()

    store2 = ConfidenceStore(path, ConfidenceConfig())
    facts = store2.facts_for_entity("Foo")
    assert len(facts) == 1
    assert facts[0].statement == "Foo uses bar"


def test_low_confidence_facts(tmp_path):
    store = make_store(tmp_path)
    store.add_fact("Low conf fact", "E", "sha1")
    store.contradict("E", "Low conf fact", "contradiction")
    store.contradict("E", "Low conf fact", "contradiction2")
    store.contradict("E", "Low conf fact", "contradiction3")
    low = store.low_confidence_facts(threshold=0.6)
    assert len(low) >= 1


def test_contradicted_facts(tmp_path):
    store = make_store(tmp_path)
    store.add_fact("Clean fact", "E", "sha1")
    store.add_fact("Dirty fact", "E", "sha2")
    store.contradict("E", "Dirty fact", "opposite")
    contradicted = store.contradicted_facts()
    assert any(f.statement == "Dirty fact" for f in contradicted)
