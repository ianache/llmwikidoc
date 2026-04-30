"""Knowledge graph — entities as nodes, typed relationships as edges."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx


VALID_RELATION_TYPES = {
    "uses", "depends_on", "modifies", "fixes", "implements",
    "calls", "extends", "contradicts", "supersedes", "related_to",
}


class KnowledgeGraph:
    """Persisted directed graph of project entities and their relationships."""

    def __init__(self, graph_path: Path) -> None:
        self.path = graph_path
        self._graph: nx.DiGraph = nx.DiGraph()
        if graph_path.exists():
            self._load()

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add_entity(self, name: str, entity_type: str, description: str = "") -> None:
        """Add or update an entity node."""
        if self._graph.has_node(name):
            # Update attributes
            self._graph.nodes[name]["type"] = entity_type
            if description:
                self._graph.nodes[name]["description"] = description
        else:
            self._graph.add_node(name, type=entity_type, description=description)

    def add_relation(
        self,
        from_entity: str,
        to_entity: str,
        relation_type: str,
        source_sha: str = "",
    ) -> None:
        """Add a typed directed edge between two entities."""
        if relation_type not in VALID_RELATION_TYPES:
            relation_type = "related_to"

        # Ensure nodes exist
        if not self._graph.has_node(from_entity):
            self._graph.add_node(from_entity, type="unknown", description="")
        if not self._graph.has_node(to_entity):
            self._graph.add_node(to_entity, type="unknown", description="")

        self._graph.add_edge(
            from_entity, to_entity,
            type=relation_type,
            source=source_sha,
        )

    # ── Query ─────────────────────────────────────────────────────────────────

    def neighbors(self, entity: str, relation_type: str | None = None) -> list[str]:
        """Return entities directly connected from the given entity."""
        if not self._graph.has_node(entity):
            return []
        edges = self._graph.out_edges(entity, data=True)
        if relation_type:
            return [v for _, v, d in edges if d.get("type") == relation_type]
        return [v for _, v, _ in edges]

    def dependents(self, entity: str) -> list[str]:
        """Return entities that depend on the given entity (reverse edges)."""
        if not self._graph.has_node(entity):
            return []
        return [u for u, _, d in self._graph.in_edges(entity, data=True)]

    def find_path(self, from_entity: str, to_entity: str) -> list[str]:
        """Find the shortest path between two entities."""
        try:
            return nx.shortest_path(self._graph, from_entity, to_entity)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def entity_info(self, name: str) -> dict[str, Any] | None:
        if not self._graph.has_node(name):
            return None
        node_data = dict(self._graph.nodes[name])
        node_data["name"] = name
        node_data["out_edges"] = [
            {"to": v, "type": d.get("type")}
            for _, v, d in self._graph.out_edges(name, data=True)
        ]
        node_data["in_edges"] = [
            {"from": u, "type": d.get("type")}
            for u, _, d in self._graph.in_edges(name, data=True)
        ]
        return node_data

    def search_entities(self, query: str) -> list[str]:
        """Return entity names that contain the query string (case-insensitive)."""
        q = query.lower()
        return [n for n in self._graph.nodes if q in n.lower()]

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self._graph, edges="edges")
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self._graph = nx.node_link_graph(raw, directed=True, edges="edges")
