"""Snapshot ingestion: scan all project files and update the wiki from current state."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llmwikidoc.config import Config
from llmwikidoc.confidence import ConfidenceStore
from llmwikidoc.graph import KnowledgeGraph
from llmwikidoc.llm import LLMClient
from llmwikidoc.wiki import WikiManager

# File extensions considered processable source/config/doc files
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go",
    ".toml", ".json", ".yaml", ".yml", ".md",
    ".sh", ".bash", ".rs", ".java", ".kt", ".rb", ".php", ".cs", ".cpp", ".c", ".h",
})

# Directories always excluded regardless of wiki_dir setting
EXCLUDED_DIRS: frozenset[str] = frozenset({
    ".git", ".venv", "venv", ".env",
    "__pycache__", "*.egg-info",
    "dist", "build", "wheels",
    "node_modules", ".next", ".nuxt",
    ".codegraph", ".claude",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "coverage", ".coverage",
})

# Files to always skip
EXCLUDED_FILES: frozenset[str] = frozenset({
    "uv.lock", "package-lock.json", "yarn.lock", "poetry.lock", "Pipfile.lock",
    "*.pyc", "*.pyo",
})

_BATCH_CHAR_BUDGET = 10_000


@dataclass
class IngestAllFilesResult:
    snapshot_id: str
    files_processed: int
    files_skipped: int
    batches: int
    pages_created: list[str] = field(default_factory=list)
    pages_updated: list[str] = field(default_factory=list)
    entities_found: int = 0
    facts_added: int = 0
    errors: list[str] = field(default_factory=list)


def ingest_all_files(config: Config) -> IngestAllFilesResult:
    """
    Scan all project files (excluding wiki/) and update the wiki from their current contents.

    Groups files by directory into batches, calls Gemini once per batch, and
    applies the same entity/relation/fact extraction as commit-based ingest.
    """
    wiki_prefix = config.wiki_dir.rstrip("/") + "/"
    extra_excludes = {config.wiki_dir, config.wiki_dir.rstrip("/")}

    files = scan_files(config.project_root, extra_excludes=extra_excludes)
    batches = _batch_files(files, config.project_root)

    wiki = WikiManager(config.wiki_path)
    graph = KnowledgeGraph(config.wiki_path / "graph.json")
    store = ConfidenceStore(config.wiki_path / "confidence.json", config.confidence)

    snapshot_id = datetime.now(timezone.utc).strftime("snapshot-%Y%m%d-%H%M%S")

    pages_created: list[str] = []
    pages_updated: list[str] = []
    facts_added = 0
    entities_found = 0
    errors: list[str] = []
    files_skipped = 0

    with LLMClient(config) as llm:
        for batch in batches:
            if not batch:
                continue
            try:
                extraction = _extract_from_files(llm, batch, config.project_root)
            except Exception as exc:
                label = str(list(batch.keys())[:2])
                errors.append(f"Batch {label}: {exc}")
                files_skipped += len(batch)
                continue

            _apply_extraction(
                extraction, snapshot_id, wiki, graph, store,
                pages_created, pages_updated,
            )
            facts_added += sum(1 for _ in extraction.get("facts", []))
            entities_found += len(extraction.get("entities", []))

    graph.save()
    store.save()

    total_files = sum(len(b) for b in batches)
    wiki.append_log(
        "INGESTALL",
        snapshot_id,
        f"{total_files - files_skipped} files, {len(pages_created)} created, "
        f"{len(pages_updated)} updated",
    )

    return IngestAllFilesResult(
        snapshot_id=snapshot_id,
        files_processed=total_files - files_skipped,
        files_skipped=files_skipped,
        batches=len(batches),
        pages_created=pages_created,
        pages_updated=pages_updated,
        entities_found=entities_found,
        facts_added=facts_added,
        errors=errors,
    )


# ── File scanning ─────────────────────────────────────────────────────────────

def scan_files(
    project_root: Path,
    extra_excludes: set[str] | None = None,
) -> list[Path]:
    """
    Return all processable files under project_root, sorted by path.

    Excludes EXCLUDED_DIRS, EXCLUDED_FILES, unsupported extensions,
    and any directories in extra_excludes.
    """
    excluded_dirs = EXCLUDED_DIRS | (extra_excludes or set())
    result: list[Path] = []

    for path in sorted(project_root.rglob("*")):
        if not path.is_file():
            continue
        # Skip if any ancestor dir matches excluded names
        rel = path.relative_to(project_root)
        if any(part in excluded_dirs for part in rel.parts[:-1]):
            continue
        if path.name in EXCLUDED_FILES:
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        # Skip very large files (>100 KB) — likely generated
        if path.stat().st_size > 100_000:
            continue
        result.append(path)

    return result


# ── Batching ──────────────────────────────────────────────────────────────────

def _batch_files(
    files: list[Path],
    project_root: Path,
    budget: int = _BATCH_CHAR_BUDGET,
) -> list[dict[str, str]]:
    """
    Group files into batches by parent directory, splitting when char budget is exceeded.
    Returns a list of {rel_path: content} dicts.
    """
    # Group by parent directory
    by_dir: dict[Path, list[Path]] = {}
    for f in files:
        by_dir.setdefault(f.parent, []).append(f)

    batches: list[dict[str, str]] = []

    for dir_files in by_dir.values():
        current_batch: dict[str, str] = {}
        current_chars = 0

        for path in dir_files:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = str(path.relative_to(project_root)).replace("\\", "/")
            chunk = content[:budget]  # cap individual file at full budget
            if current_chars + len(chunk) > budget and current_batch:
                batches.append(current_batch)
                current_batch = {}
                current_chars = 0
            current_batch[rel] = chunk
            current_chars += len(chunk)

        if current_batch:
            batches.append(current_batch)

    return batches


# ── LLM extraction ────────────────────────────────────────────────────────────

def _extract_from_files(
    llm: LLMClient,
    files: dict[str, str],
    project_root: Path,
) -> dict[str, Any]:
    prompt = _build_file_extraction_prompt(files)
    try:
        return llm.generate_structured(prompt)
    except ValueError:
        return {"summary": "", "entities": [], "relations": [], "facts": [], "contradictions": []}


def _build_file_extraction_prompt(files: dict[str, str]) -> str:
    file_list = ", ".join(files.keys())
    files_section = _format_files(files)

    return textwrap.dedent(f"""
        You are a technical documentation assistant analyzing source files to build a project wiki.

        ## Files Being Analyzed
        {file_list}

        ## File Contents
        {files_section}

        ## Task
        Analyze these files and extract structured information for a project wiki.
        Return a JSON object with exactly this structure:

        {{
          "summary": "One sentence describing what this group of files does",
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
          "contradictions": []
        }}

        Rules:
        - Only include entities actually defined or used in these files
        - Facts must be specific and verifiable (not vague opinions)
        - Return valid JSON only, no markdown code fences
    """).strip()


def _format_files(files: dict[str, str]) -> str:
    parts = [f"### {path}\n```\n{content}\n```" for path, content in files.items()]
    return "\n\n".join(parts)


# ── Wiki update ───────────────────────────────────────────────────────────────

def _apply_extraction(
    extraction: dict[str, Any],
    snapshot_id: str,
    wiki: WikiManager,
    graph: KnowledgeGraph,
    store: ConfidenceStore,
    pages_created: list[str],
    pages_updated: list[str],
) -> None:
    for entity in extraction.get("entities", []):
        name = entity.get("name", "").strip()
        etype = entity.get("type", "concept")
        description = entity.get("description", "")
        if not name:
            continue

        subdir = "entities" if etype in {"class", "function", "module"} else "concepts"
        page_type = etype if etype in {"class", "function", "module"} else "concept"

        body = (
            f"# {name}\n\n{description}\n\n"
            f"## References\n\n- [snapshot: {snapshot_id}]\n"
        )
        page = wiki.create_or_update_page(
            subdir=subdir,
            name=name,
            body=body,
            page_type=page_type,
            sources=[snapshot_id],
        )
        wiki.update_index(name, page_type, subdir, description[:80])

        if page.frontmatter.get("created") == page.frontmatter.get("updated"):
            pages_created.append(f"{subdir}/{name}")
        else:
            pages_updated.append(f"{subdir}/{name}")

        graph.add_entity(name, etype, description)

    for rel in extraction.get("relations", []):
        from_e = rel.get("from", "").strip()
        to_e = rel.get("to", "").strip()
        rel_type = rel.get("type", "related_to")
        if from_e and to_e:
            graph.add_relation(from_e, to_e, rel_type, source_sha=snapshot_id)

    for fact_data in extraction.get("facts", []):
        statement = fact_data.get("statement", "").strip()
        entity = fact_data.get("entity", "").strip()
        if statement and entity:
            store.add_fact(statement, entity, snapshot_id)
