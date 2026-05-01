"""Ingestion pipeline: git commit → LLM extraction → wiki update."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llmwikidoc.config import Config
from llmwikidoc.confidence import ConfidenceStore
from llmwikidoc.git_reader import CommitContext, read_commit
from llmwikidoc.graph import KnowledgeGraph
from llmwikidoc.llm import LLMClient
from llmwikidoc.wiki import WikiManager


@dataclass
class IngestResult:
    sha: str
    short_sha: str
    pages_created: list[str]
    pages_updated: list[str]
    entities_found: int
    facts_added: int
    contradictions: int
    errors: list[str]


class SkippedCommit(Exception):
    """Raised when a commit has no relevant changes after filtering."""


def ingest_commit(
    config: Config,
    sha: str | None = None,
    exclude_prefixes: list[str] | None = None,
) -> IngestResult:
    """
    Full pipeline: read commit → extract with Gemini → update wiki.

    Args:
        config: Project configuration.
        sha: Commit SHA to ingest. Defaults to HEAD.
        exclude_prefixes: File path prefixes to ignore (e.g. ["wiki/"]).

    Raises:
        SkippedCommit: If all changed files were excluded (nothing to ingest).
    """
    errors: list[str] = []

    # 1. Read commit context
    ctx = read_commit(
        config.project_root,
        sha=sha,
        context_depth=config.context_depth,
        exclude_prefixes=exclude_prefixes,
    )

    if not ctx.changed_files:
        raise SkippedCommit(f"No relevant files in commit {ctx.short_sha} after filtering")

    # 2. Build prompt and call Gemini
    with LLMClient(config) as llm:
        extraction = _extract(llm, ctx)

    # 3. Initialize wiki components
    wiki = WikiManager(config.wiki_path)
    graph = KnowledgeGraph(config.wiki_path / "graph.json")
    store = ConfidenceStore(
        config.wiki_path / "confidence.json",
        config.confidence,
    )

    pages_created: list[str] = []
    pages_updated: list[str] = []
    facts_added = 0
    contradictions = 0

    # 4. Create commit summary page
    summary_body = _build_summary_body(ctx, extraction)
    wiki.create_summary(ctx.short_sha, summary_body, ctx.sha)
    pages_created.append(f"summaries/{ctx.short_sha}")

    # 5. Create/update entity pages
    for entity in extraction.get("entities", []):
        name = entity.get("name", "").strip()
        etype = entity.get("type", "concept")
        description = entity.get("description", "")
        if not name:
            continue

        subdir = "entities" if etype in {"class", "function", "module"} else "concepts"
        page_type = etype if etype in {"class", "function", "module"} else "concept"

        body = f"# {name}\n\n{description}\n\n## References\n\n- [{ctx.short_sha}](../summaries/{ctx.short_sha}.md)\n"
        page = wiki.create_or_update_page(
            subdir=subdir,
            name=name,
            body=body,
            page_type=page_type,
            sources=[ctx.sha],
        )
        wiki.update_index(name, page_type, subdir, description[:80])

        if page.frontmatter.get("created") == page.frontmatter.get("updated"):
            pages_created.append(f"{subdir}/{name}")
        else:
            pages_updated.append(f"{subdir}/{name}")

        graph.add_entity(name, etype, description)

    # 6. Add relations to knowledge graph
    for rel in extraction.get("relations", []):
        from_e = rel.get("from", "").strip()
        to_e = rel.get("to", "").strip()
        rel_type = rel.get("type", "related_to")
        if from_e and to_e:
            graph.add_relation(from_e, to_e, rel_type, source_sha=ctx.short_sha)

    # 7. Process facts and confidence scores
    for fact_data in extraction.get("facts", []):
        statement = fact_data.get("statement", "").strip()
        entity = fact_data.get("entity", "").strip()
        if not statement or not entity:
            continue
        store.add_fact(statement, entity, ctx.sha)
        facts_added += 1

    # 8. Handle contradictions
    for contradiction in extraction.get("contradictions", []):
        fact = contradiction.get("fact", "").strip()
        conflicts_with = contradiction.get("conflicts_with", "").strip()
        entity = contradiction.get("entity", "").strip()
        if fact and conflicts_with and entity:
            store.contradict(entity, conflicts_with, fact)
            contradictions += 1

    # 9. Save everything
    graph.save()
    store.save()

    # 10. Append to log
    summary_line = extraction.get("summary", ctx.message[:80])
    wiki.append_log(
        "INGEST",
        ctx.sha,
        f"{len(pages_created)} created, {len(pages_updated)} updated | {summary_line}",
    )

    return IngestResult(
        sha=ctx.sha,
        short_sha=ctx.short_sha,
        pages_created=pages_created,
        pages_updated=pages_updated,
        entities_found=len(extraction.get("entities", [])),
        facts_added=facts_added,
        contradictions=contradictions,
        errors=errors,
    )


# ── LLM Extraction ────────────────────────────────────────────────────────────

def _extract(llm: LLMClient, ctx: CommitContext) -> dict[str, Any]:
    """Build prompt with full commit context and call Gemini for structured extraction."""
    prompt = _build_extraction_prompt(ctx)
    try:
        return llm.generate_structured(prompt)
    except ValueError:
        # Fallback: minimal extraction from commit message only
        return {
            "summary": ctx.message[:200],
            "entities": [],
            "relations": [],
            "facts": [],
            "contradictions": [],
        }


def _build_extraction_prompt(ctx: CommitContext) -> str:
    # Truncate large contents to avoid token limits
    diff_preview = ctx.diff[:6000] if len(ctx.diff) > 6000 else ctx.diff
    files_section = _format_file_contents(ctx.file_contents, max_chars=8000)
    related_section = _format_file_contents(ctx.related_files, max_chars=4000)

    return textwrap.dedent(f"""
        You are a technical documentation assistant analyzing a git commit to update a project wiki.

        ## Commit Information
        SHA: {ctx.sha}
        Author: {ctx.author}
        Timestamp: {ctx.timestamp}
        Message: {ctx.message}

        ## Changed Files
        {', '.join(ctx.changed_files) or 'none'}

        ## Diff
        ```diff
        {diff_preview}
        ```

        ## Full Content of Modified Files
        {files_section}

        ## Related Files (context)
        {related_section}

        ## Task
        Analyze this commit and extract structured information for a project wiki.
        Return a JSON object with exactly this structure:

        {{
          "summary": "One clear sentence describing what this commit does and why",
          "entities": [
            {{
              "name": "EntityName",
              "type": "class|function|module|decision|concept",
              "description": "Clear description of this entity and its purpose"
            }}
          ],
          "relations": [
            {{
              "from": "EntityA",
              "to": "EntityB",
              "type": "uses|depends_on|modifies|fixes|implements|calls|extends|related_to"
            }}
          ],
          "facts": [
            {{
              "statement": "A specific, verifiable fact about the codebase",
              "entity": "EntityName this fact belongs to",
              "confidence": 0.7
            }}
          ],
          "contradictions": [
            {{
              "fact": "New claim from this commit",
              "conflicts_with": "Existing claim that contradicts it",
              "entity": "EntityName"
            }}
          ]
        }}

        Rules:
        - Only include entities actually present in the changed/related files
        - Facts must be specific and verifiable (not vague opinions)
        - Only include contradictions if you can identify an existing conflicting claim
        - Return valid JSON only, no markdown code fences
    """).strip()


def _format_file_contents(files: dict[str, str], max_chars: int) -> str:
    if not files:
        return "(none)"
    parts: list[str] = []
    budget = max_chars
    for path, content in files.items():
        if budget <= 0:
            parts.append(f"[{path}] (truncated — budget exhausted)")
            break
        chunk = content[:budget]
        parts.append(f"### {path}\n```\n{chunk}\n```")
        budget -= len(chunk)
    return "\n\n".join(parts)


def _build_summary_body(ctx: CommitContext, extraction: dict[str, Any]) -> str:
    summary = extraction.get("summary", ctx.message)
    entities = extraction.get("entities", [])
    entity_list = "\n".join(
        f"- **{e['name']}** ({e.get('type', '?')}): {e.get('description', '')}"
        for e in entities
    ) or "_none detected_"

    changed = "\n".join(f"- `{f}`" for f in ctx.changed_files) or "_none_"

    return textwrap.dedent(f"""
        # Commit {ctx.short_sha}

        **{ctx.message}**

        {summary}

        ## Changed Files
        {changed}

        ## Entities
        {entity_list}

        ## Stats
        - Author: {ctx.author}
        - Timestamp: {ctx.timestamp}
        - Files changed: {len(ctx.changed_files)}
    """).strip() + "\n"
