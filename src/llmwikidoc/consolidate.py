"""
Consolidation tiers and Ebbinghaus retention decay.

Memory lifecycle:
  working   → facts from recent commits, high volume, low compression
  episodic  → summaries of sessions/sprints, moderate compression
  semantic  → distilled concepts across episodes, high compression
  procedural→ stable high-confidence patterns, permanent

Transition thresholds (configurable via .llmwikidoc.toml in future):
  working   → episodic : facts older than WORKING_TTL_DAYS with confidence > 0.5
  episodic  → semantic : pages older than EPISODIC_TTL_DAYS with ≥3 supporting sources
  semantic  → procedural: confidence ≥ PROCEDURAL_THRESHOLD and age ≥ SEMANTIC_TTL_DAYS
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llmwikidoc.confidence import ConfidenceStore, Fact
from llmwikidoc.wiki import WikiManager, WikiPage

# Tier transition thresholds
WORKING_TTL_DAYS = 7
EPISODIC_TTL_DAYS = 30
SEMANTIC_TTL_DAYS = 90
PROCEDURAL_THRESHOLD = 0.85

TIER_ORDER = ["working", "episodic", "semantic", "procedural"]


@dataclass
class ConsolidationResult:
    facts_decayed: int = 0
    facts_promoted: int = 0        # working → episodic
    pages_promoted: int = 0        # episodic → semantic or semantic → procedural
    pages_compressed: list[str] = field(default_factory=list)
    decay_warnings: list[str] = field(default_factory=list)  # facts that fell below 0.3


# ── Public API ────────────────────────────────────────────────────────────────

def run_consolidation(
    wiki: WikiManager,
    store: ConfidenceStore,
    llm: Any | None = None,         # LLMClient, optional for LLM-assisted compression
) -> ConsolidationResult:
    """
    Run a full consolidation cycle:
    1. Apply Ebbinghaus decay to all facts
    2. Promote eligible working facts to episodic tier
    3. Promote eligible episodic pages to semantic tier
    4. Promote eligible semantic pages to procedural tier
    """
    result = ConsolidationResult()

    # 1. Decay
    _apply_decay(store, result)

    # 2. Promote facts: working → episodic
    _promote_facts(store, result)

    # 3. Promote pages: episodic → semantic → procedural
    _promote_pages(wiki, store, result, llm=llm)

    # Persist updated confidence scores
    store.save()

    return result


# ── Ebbinghaus Decay ──────────────────────────────────────────────────────────

def _apply_decay(store: ConfidenceStore, result: ConsolidationResult) -> None:
    """
    Apply time-based forgetting curve to all facts.

    Ebbinghaus model (simplified):
      confidence_new = confidence * e^(-elapsed_days / stability)

    where stability = decay_days from config (default 30).
    Facts in episodic/semantic/procedural tiers decay slower.
    """
    now = datetime.now(timezone.utc)
    stability = store.config.decay_days

    for fact in store._facts.values():
        tier = _fact_tier(fact)
        tier_multiplier = _tier_stability_multiplier(tier)
        effective_stability = stability * tier_multiplier

        try:
            last = datetime.fromisoformat(
                fact.last_reinforced.replace("Z", "+00:00")
            )
            elapsed_days = (now - last).total_seconds() / 86400
        except ValueError:
            elapsed_days = 0.0

        if elapsed_days < 1.0:
            continue

        # Ebbinghaus exponential decay
        retention = math.exp(-elapsed_days / effective_stability)
        new_confidence = fact.confidence * retention

        if new_confidence < fact.confidence:
            fact.confidence = max(0.0, round(new_confidence, 3))
            result.facts_decayed += 1

            if fact.confidence < 0.3:
                result.decay_warnings.append(
                    f"{fact.entity}: \"{fact.statement[:60]}\" → {fact.confidence:.2f}"
                )


def _tier_stability_multiplier(tier: str) -> float:
    """Higher tiers decay more slowly."""
    return {
        "working": 1.0,
        "episodic": 2.0,
        "semantic": 4.0,
        "procedural": 10.0,
    }.get(tier, 1.0)


def _fact_tier(fact: Fact) -> str:
    """Infer tier from number of sources and confidence (facts don't store tier directly)."""
    if len(fact.sources) >= 5 and fact.confidence >= PROCEDURAL_THRESHOLD:
        return "procedural"
    if len(fact.sources) >= 3:
        return "semantic"
    if len(fact.sources) >= 2:
        return "episodic"
    return "working"


# ── Fact promotion: working → episodic ───────────────────────────────────────

def _promote_facts(store: ConfidenceStore, result: ConsolidationResult) -> None:
    """
    Group working-tier facts by entity and merge related ones.
    A fact graduates from working to episodic when:
      - It has been reinforced (≥2 sources) and confidence ≥ 0.5
      - OR it's older than WORKING_TTL_DAYS and confidence ≥ 0.6
    """
    now = datetime.now(timezone.utc)

    for fact in store._facts.values():
        if _fact_tier(fact) != "working":
            continue

        try:
            created = datetime.fromisoformat(
                fact.created.replace("Z", "+00:00")
            )
            age_days = (now - created).total_seconds() / 86400
        except ValueError:
            age_days = 0.0

        promoted = False
        if len(fact.sources) >= 2 and fact.confidence >= 0.5:
            promoted = True
        elif age_days >= WORKING_TTL_DAYS and fact.confidence >= 0.6:
            promoted = True

        if promoted:
            # Graduation: mark in sources count by adding synthetic "consolidated" marker
            if "consolidated" not in fact.sources:
                fact.sources.append("consolidated")
                result.facts_promoted += 1


# ── Page promotion: episodic → semantic → procedural ────────────────────────

def _promote_pages(
    wiki: WikiManager,
    store: ConfidenceStore,
    result: ConsolidationResult,
    llm: Any | None = None,
) -> None:
    """Scan wiki pages and promote tiers based on age and confidence."""
    now = datetime.now(timezone.utc)
    pages = wiki.all_pages()

    for page in pages:
        current_tier = str(page.frontmatter.get("tier", "working"))
        if current_tier == "procedural":
            continue

        confidence = float(page.frontmatter.get("confidence", 0.5))
        sources: list[str] = page.frontmatter.get("sources", [])

        try:
            updated_str = str(page.frontmatter.get("updated", ""))
            updated = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
            age_days = (now - updated).total_seconds() / 86400
        except ValueError:
            age_days = 0.0

        new_tier = _compute_new_tier(current_tier, confidence, sources, age_days)

        if new_tier != current_tier:
            page.frontmatter["tier"] = new_tier
            # Compress body if promoting to semantic+ and LLM available
            if new_tier in {"semantic", "procedural"} and llm is not None:
                compressed_body = _compress_page(page, new_tier, llm)
                if compressed_body:
                    page.body = compressed_body
                    result.pages_compressed.append(page.path.stem)

            page.save()
            result.pages_promoted += 1


def _compute_new_tier(
    current_tier: str,
    confidence: float,
    sources: list[str],
    age_days: float,
) -> str:
    if current_tier == "working":
        if len(sources) >= 3 and confidence >= 0.6:
            return "episodic"
        if age_days >= WORKING_TTL_DAYS and confidence >= 0.5:
            return "episodic"

    elif current_tier == "episodic":
        if len(sources) >= 5 and confidence >= 0.7:
            return "semantic"
        if age_days >= EPISODIC_TTL_DAYS and confidence >= 0.65:
            return "semantic"

    elif current_tier == "semantic":
        if confidence >= PROCEDURAL_THRESHOLD and age_days >= SEMANTIC_TTL_DAYS:
            return "procedural"

    return current_tier


def _compress_page(page: WikiPage, target_tier: str, llm: Any) -> str | None:
    """Use LLM to compress a page body for higher-tier storage."""
    instruction = {
        "semantic": (
            "Compress this wiki page to its essential facts and relationships. "
            "Remove implementation details. Keep: core concept, key relationships, "
            "why it matters. Target: 30% of original length."
        ),
        "procedural": (
            "Distill this wiki page to a single permanent reference entry. "
            "Keep only the stable, timeless facts. Remove all temporal or "
            "commit-specific references. Target: 10-15% of original length."
        ),
    }.get(target_tier)

    if not instruction:
        return None

    prompt = (
        f"## Task\n{instruction}\n\n"
        f"## Current page ({page.path.stem})\n\n{page.body}"
    )
    try:
        return llm.generate(prompt)
    except Exception:
        return None


# ── Session Digest ────────────────────────────────────────────────────────────

@dataclass
class DigestResult:
    digest_page: str
    commits_covered: int
    entities_mentioned: int
    new_facts: int


def create_digest(
    wiki: WikiManager,
    store: ConfidenceStore,
    llm: Any,
    n_recent: int = 10,
) -> DigestResult:
    """
    Crystallize the N most recent commit summaries into a structured digest.

    The digest:
    - Identifies the key themes across N commits
    - Extracts new durable facts and adds them to the confidence store
    - Creates a semantic-tier page that acts as a new source
    - Reinforces facts mentioned across multiple commits
    """
    from llmwikidoc.wiki import _now_iso

    # Collect recent summaries
    summary_pages = sorted(
        [p for p in wiki.all_pages() if p.frontmatter.get("type") == "summary"],
        key=lambda p: p.frontmatter.get("created", ""),
        reverse=True,
    )[:n_recent]

    if not summary_pages:
        raise ValueError("No commit summaries found in wiki. Run ingest first.")

    # Build context for LLM
    summaries_text = "\n\n---\n\n".join(
        f"## {p.path.stem}\n{p.body[:1500]}" for p in summary_pages
    )

    prompt = f"""You are distilling {len(summary_pages)} git commit summaries into a structured knowledge digest.

## Commit Summaries
{summaries_text}

## Task
Analyze these commits and produce a JSON digest with this structure:
{{
  "title": "Concise title for this development session",
  "period_summary": "2-3 sentence overview of what was accomplished",
  "key_themes": ["theme1", "theme2"],
  "entities_changed": [{{"name": "EntityName", "type": "class|function|module", "changes": "what changed"}}],
  "durable_facts": [{{"statement": "Stable fact about the codebase", "entity": "EntityName", "confidence": 0.8}}],
  "open_questions": ["question1"],
  "next_steps": ["step1"]
}}

Rules:
- durable_facts must be stable truths, not ephemeral commit details
- confidence should reflect how certain you are based on the evidence
- Return valid JSON only"""

    raw = llm.generate_structured(prompt)

    # Build digest markdown
    title = raw.get("title", f"Digest — {len(summary_pages)} commits")
    period_summary = raw.get("period_summary", "")
    themes = raw.get("key_themes", [])
    entities = raw.get("entities_changed", [])
    durable_facts = raw.get("durable_facts", [])
    questions = raw.get("open_questions", [])
    next_steps = raw.get("next_steps", [])

    themes_md = "\n".join(f"- {t}" for t in themes) or "_none_"
    entities_md = "\n".join(
        f"- **{e.get('name', '?')}** ({e.get('type', '?')}): {e.get('changes', '')}"
        for e in entities
    ) or "_none_"
    facts_md = "\n".join(
        f"- {f.get('statement', '')} _(confidence: {f.get('confidence', 0.7):.0%})_"
        for f in durable_facts
    ) or "_none_"
    questions_md = "\n".join(f"- {q}" for q in questions) or "_none_"
    steps_md = "\n".join(f"- {s}" for s in next_steps) or "_none_"

    now = _now_iso()
    digest_name = f"digest_{now[:10].replace('-', '')}"
    body = f"""# {title}

{period_summary}

## Key Themes
{themes_md}

## Entities Changed
{entities_md}

## Durable Facts
{facts_md}

## Open Questions
{questions_md}

## Next Steps
{steps_md}

## Source Commits
{', '.join(p.path.stem for p in summary_pages)}
"""

    # Save digest as semantic-tier concept page
    digest_sources = [p.frontmatter.get("sha", p.path.stem) for p in summary_pages]
    wiki.create_or_update_page(
        subdir="concepts",
        name=digest_name,
        body=body,
        page_type="digest",
        sources=digest_sources,
        confidence=0.8,
        tier="semantic",
    )
    wiki.update_index(digest_name, "digest", "concepts", title[:80])

    # Store durable facts and reinforce existing ones
    new_facts = 0
    for fact_data in durable_facts:
        statement = fact_data.get("statement", "").strip()
        entity = fact_data.get("entity", "").strip()
        if not statement or not entity:
            continue
        existing = store.facts_for_entity(entity)
        matched = next(
            (f for f in existing if statement[:40].lower() in f.statement.lower()), None
        )
        if matched:
            store.reinforce(entity, matched.statement, digest_name)
        else:
            store.add_fact(statement, entity, digest_name)
            new_facts += 1

    store.save()
    wiki.append_log(
        "DIGEST",
        digest_name,
        f"{len(summary_pages)} commits → {new_facts} new facts, {len(entities)} entities",
    )

    return DigestResult(
        digest_page=digest_name,
        commits_covered=len(summary_pages),
        entities_mentioned=len(entities),
        new_facts=new_facts,
    )
