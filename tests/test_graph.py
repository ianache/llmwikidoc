"""Tests for graph.py."""

from pathlib import Path
from llmwikidoc.graph import KnowledgeGraph


def test_add_entity(tmp_path):
    g = KnowledgeGraph(tmp_path / "graph.json")
    g.add_entity("UserService", "class", "Handles user auth")
    assert g.node_count == 1


def test_add_relation_creates_nodes(tmp_path):
    g = KnowledgeGraph(tmp_path / "graph.json")
    g.add_relation("UserService", "Database", "depends_on")
    assert g.node_count == 2
    assert g.edge_count == 1


def test_neighbors(tmp_path):
    g = KnowledgeGraph(tmp_path / "graph.json")
    g.add_relation("A", "B", "uses")
    g.add_relation("A", "C", "depends_on")
    neighbors = g.neighbors("A")
    assert set(neighbors) == {"B", "C"}


def test_neighbors_filtered_by_type(tmp_path):
    g = KnowledgeGraph(tmp_path / "graph.json")
    g.add_relation("A", "B", "uses")
    g.add_relation("A", "C", "depends_on")
    assert g.neighbors("A", relation_type="uses") == ["B"]
    assert g.neighbors("A", relation_type="depends_on") == ["C"]


def test_dependents(tmp_path):
    g = KnowledgeGraph(tmp_path / "graph.json")
    g.add_relation("A", "C", "uses")
    g.add_relation("B", "C", "uses")
    assert set(g.dependents("C")) == {"A", "B"}


def test_invalid_relation_type_falls_back(tmp_path):
    g = KnowledgeGraph(tmp_path / "graph.json")
    g.add_relation("A", "B", "invented_type")
    info = g.entity_info("A")
    assert info["out_edges"][0]["type"] == "related_to"


def test_persist_and_reload(tmp_path):
    path = tmp_path / "graph.json"
    g = KnowledgeGraph(path)
    g.add_entity("Foo", "class", "A class")
    g.add_relation("Foo", "Bar", "uses")
    g.save()

    g2 = KnowledgeGraph(path)
    assert g2.node_count == 2
    assert g2.edge_count == 1
    assert g2.neighbors("Foo") == ["Bar"]


def test_find_path(tmp_path):
    g = KnowledgeGraph(tmp_path / "graph.json")
    g.add_relation("A", "B", "uses")
    g.add_relation("B", "C", "uses")
    path = g.find_path("A", "C")
    assert path == ["A", "B", "C"]


def test_search_entities(tmp_path):
    g = KnowledgeGraph(tmp_path / "graph.json")
    g.add_entity("UserService", "class")
    g.add_entity("UserController", "class")
    g.add_entity("PaymentService", "class")
    results = g.search_entities("user")
    assert "UserService" in results
    assert "UserController" in results
    assert "PaymentService" not in results
