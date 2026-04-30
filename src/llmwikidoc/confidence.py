"""Confidence scoring for wiki facts — reinforcement, decay, contradiction handling."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llmwikidoc.config import ConfidenceConfig


@dataclass
class Fact:
    statement: str
    entity: str
    confidence: float
    sources: list[str] = field(default_factory=list)
    created: str = field(default_factory=lambda: _now_iso())
    last_reinforced: str = field(default_factory=lambda: _now_iso())
    contradicted_by: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement": self.statement,
            "entity": self.entity,
            "confidence": round(self.confidence, 3),
            "sources": self.sources,
            "created": self.created,
            "last_reinforced": self.last_reinforced,
            "contradicted_by": self.contradicted_by,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Fact:
        return cls(
            statement=d["statement"],
            entity=d["entity"],
            confidence=d["confidence"],
            sources=d.get("sources", []),
            created=d.get("created", _now_iso()),
            last_reinforced=d.get("last_reinforced", _now_iso()),
            contradicted_by=d.get("contradicted_by", []),
        )


class ConfidenceStore:
    """Manages fact confidence scores with reinforcement and decay."""

    def __init__(self, store_path: Path, config: ConfidenceConfig) -> None:
        self.path = store_path
        self.config = config
        self._facts: dict[str, Fact] = {}  # key: entity::statement_hash
        if store_path.exists():
            self._load()

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add_fact(self, statement: str, entity: str, source_sha: str) -> Fact:
        """Add a new fact with initial confidence, or reinforce if it already exists."""
        key = _fact_key(entity, statement)
        if key in self._facts:
            return self.reinforce(entity, statement, source_sha)

        fact = Fact(
            statement=statement,
            entity=entity,
            confidence=self.config.initial,
            sources=[source_sha],
        )
        self._facts[key] = fact
        return fact

    def reinforce(self, entity: str, statement: str, source_sha: str) -> Fact:
        """Boost confidence when a fact is confirmed by a new source."""
        key = _fact_key(entity, statement)
        if key not in self._facts:
            return self.add_fact(statement, entity, source_sha)

        fact = self._facts[key]
        fact.confidence = min(1.0, fact.confidence + self.config.reinforce_delta)
        fact.last_reinforced = _now_iso()
        if source_sha not in fact.sources:
            fact.sources.append(source_sha)
        return fact

    def contradict(self, entity: str, statement: str, contradicting_statement: str) -> Fact | None:
        """Lower confidence when a fact is contradicted."""
        key = _fact_key(entity, statement)
        if key not in self._facts:
            return None

        fact = self._facts[key]
        fact.confidence = max(0.0, fact.confidence + self.config.contradict_delta)
        if contradicting_statement not in fact.contradicted_by:
            fact.contradicted_by.append(contradicting_statement)
        return fact

    def apply_decay(self) -> list[Fact]:
        """Apply time-based confidence decay. Returns facts that dropped below 0.3."""
        now = datetime.now(timezone.utc)
        decayed: list[Fact] = []

        for fact in self._facts.values():
            try:
                last = datetime.fromisoformat(fact.last_reinforced.replace("Z", "+00:00"))
                days_elapsed = (now - last).days
            except ValueError:
                days_elapsed = 0

            if days_elapsed >= self.config.decay_days:
                decay_cycles = days_elapsed // self.config.decay_days
                decay_amount = 0.1 * decay_cycles
                fact.confidence = max(0.0, fact.confidence - decay_amount)
                if fact.confidence < 0.3:
                    decayed.append(fact)

        return decayed

    # ── Query ─────────────────────────────────────────────────────────────────

    def facts_for_entity(self, entity: str) -> list[Fact]:
        return [f for f in self._facts.values() if f.entity == entity]

    def low_confidence_facts(self, threshold: float = 0.4) -> list[Fact]:
        return [f for f in self._facts.values() if f.confidence < threshold]

    def contradicted_facts(self) -> list[Fact]:
        return [f for f in self._facts.values() if f.contradicted_by]

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.to_dict() for k, v in self._facts.items()}
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self._facts = {k: Fact.from_dict(v) for k, v in raw.items()}


# ── Utilities ─────────────────────────────────────────────────────────────────

def _fact_key(entity: str, statement: str) -> str:
    # Simple key: entity + first 60 chars of statement
    return f"{entity.lower()}::{statement[:60].lower()}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
