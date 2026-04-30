"""Wiki file management — CRUD for markdown pages with YAML frontmatter."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Frontmatter helpers ──────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body) from a markdown string."""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    fm: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            raw = value.strip()
            # Parse lists like: [a, b, c]
            if raw.startswith("[") and raw.endswith("]"):
                fm[key.strip()] = [v.strip() for v in raw[1:-1].split(",") if v.strip()]
            else:
                # Try numeric
                try:
                    fm[key.strip()] = float(raw) if "." in raw else int(raw)
                except ValueError:
                    fm[key.strip()] = raw
    return fm, content[match.end():]


def render_frontmatter(fm: dict[str, Any], body: str) -> str:
    """Serialize frontmatter dict + body back to a markdown string."""
    lines = ["---"]
    for key, value in fm.items():
        if isinstance(value, list):
            lines.append(f"{key}: [{', '.join(str(v) for v in value)}]")
        elif isinstance(value, float):
            lines.append(f"{key}: {value:.2f}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + body


# ── WikiPage ─────────────────────────────────────────────────────────────────

class WikiPage:
    """A single wiki page backed by a markdown file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.frontmatter: dict[str, Any] = {}
        self.body: str = ""
        if path.exists():
            self._load()

    def _load(self) -> None:
        content = self.path.read_text(encoding="utf-8")
        self.frontmatter, self.body = parse_frontmatter(content)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(render_frontmatter(self.frontmatter, self.body), encoding="utf-8")

    @property
    def exists(self) -> bool:
        return self.path.exists()


# ── WikiManager ──────────────────────────────────────────────────────────────

class WikiManager:
    """High-level interface for all wiki operations."""

    def __init__(self, wiki_path: Path) -> None:
        self.root = wiki_path
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for sub in ["entities", "concepts", "summaries"]:
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    # ── Page CRUD ────────────────────────────────────────────────────────────

    def get_page(self, subdir: str, name: str) -> WikiPage:
        safe_name = _safe_filename(name)
        return WikiPage(self.root / subdir / f"{safe_name}.md")

    def get_summary(self, short_sha: str) -> WikiPage:
        return WikiPage(self.root / "summaries" / f"{short_sha}.md")

    def create_or_update_page(
        self,
        subdir: str,
        name: str,
        body: str,
        *,
        page_type: str,
        sources: list[str] | None = None,
        related: list[str] | None = None,
        confidence: float = 0.7,
        tier: str = "working",
    ) -> WikiPage:
        page = self.get_page(subdir, name)
        now = _now_iso()

        if page.exists:
            page.frontmatter["updated"] = now
            # Keep existing created date and bump confidence slightly
            existing_conf = float(page.frontmatter.get("confidence", confidence))
            page.frontmatter["confidence"] = round(min(1.0, existing_conf + 0.05), 2)
            # Merge sources
            existing_sources: list[str] = page.frontmatter.get("sources", [])
            if sources:
                merged = list(dict.fromkeys(existing_sources + sources))
                page.frontmatter["sources"] = merged
        else:
            page.frontmatter = {
                "type": page_type,
                "name": name,
                "created": now,
                "updated": now,
                "confidence": confidence,
                "sources": sources or [],
                "related": related or [],
                "tier": tier,
            }

        page.body = body
        page.save()
        return page

    def create_summary(self, short_sha: str, body: str, sha: str) -> WikiPage:
        page = self.get_summary(short_sha)
        page.frontmatter = {
            "type": "summary",
            "name": short_sha,
            "sha": sha,
            "created": _now_iso(),
            "updated": _now_iso(),
            "confidence": 1.0,
            "sources": [sha],
            "tier": "episodic",
        }
        page.body = body
        page.save()
        return page

    def all_pages(self) -> list[WikiPage]:
        pages: list[WikiPage] = []
        for md_file in self.root.rglob("*.md"):
            if md_file.name in {"index.md", "log.md"}:
                continue
            pages.append(WikiPage(md_file))
        return pages

    # ── index.md ─────────────────────────────────────────────────────────────

    def update_index(self, name: str, page_type: str, subdir: str, summary_line: str) -> None:
        index_path = self.root / "index.md"
        entry = f"- [{name}]({subdir}/{_safe_filename(name)}.md) — {summary_line}\n"

        if not index_path.exists():
            index_path.write_text(f"# Wiki Index\n\n## {page_type.capitalize()}s\n\n{entry}", encoding="utf-8")
            return

        content = index_path.read_text(encoding="utf-8")
        section_header = f"## {page_type.capitalize()}s"

        # Update existing entry if present
        safe = _safe_filename(name)
        existing_pattern = re.compile(rf"- \[{re.escape(name)}\]\({re.escape(subdir)}/{re.escape(safe)}\.md\)[^\n]*\n")
        if existing_pattern.search(content):
            content = existing_pattern.sub(entry, content)
        elif section_header in content:
            content = content.replace(
                section_header + "\n",
                section_header + "\n\n" + entry,
            )
        else:
            content += f"\n{section_header}\n\n{entry}"

        index_path.write_text(content, encoding="utf-8")

    # ── log.md ───────────────────────────────────────────────────────────────

    def append_log(self, operation: str, sha: str, detail: str) -> None:
        log_path = self.root / "log.md"
        timestamp = _now_iso()
        entry = f"[{timestamp}] [{operation}] [{sha[:8]}] {detail}\n"

        if not log_path.exists():
            log_path.write_text("# Wiki Log\n\n" + entry, encoding="utf-8")
        else:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(entry)

    # ── Stats ────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, int]:
        pages = self.all_pages()
        by_type: dict[str, int] = {}
        for page in pages:
            t = str(page.frontmatter.get("type", "unknown"))
            by_type[t] = by_type.get(t, 0) + 1
        return by_type


# ── Utilities ─────────────────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    """Convert an entity name to a safe filename."""
    safe = re.sub(r"[^\w\s-]", "", name.lower())
    safe = re.sub(r"[\s]+", "_", safe.strip())
    return safe or "unnamed"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
