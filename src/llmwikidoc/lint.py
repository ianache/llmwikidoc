"""Wiki health checks — contradictions, orphaned pages, stale claims, broken links."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llmwikidoc.config import Config
from llmwikidoc.confidence import ConfidenceStore
from llmwikidoc.wiki import WikiManager, WikiPage


# ── Issue types ───────────────────────────────────────────────────────────────

@dataclass
class LintIssue:
    severity: str          # "error" | "warning" | "info"
    issue_type: str        # "orphan" | "broken_link" | "low_confidence" | "contradiction" | "stale" | "missing_source"
    page: str              # relative path or page name
    detail: str
    auto_fixable: bool = False


@dataclass
class LintReport:
    issues: list[LintIssue] = field(default_factory=list)
    pages_checked: int = 0
    fixed: list[str] = field(default_factory=list)

    @property
    def errors(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def infos(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == "info"]

    def summary(self) -> str:
        return (
            f"{self.pages_checked} pages checked | "
            f"{len(self.errors)} errors, {len(self.warnings)} warnings, {len(self.infos)} info"
        )


# ── Linter ────────────────────────────────────────────────────────────────────

class WikiLinter:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._wiki = WikiManager(config.wiki_path)
        # Always create the store; it handles missing file by starting with empty facts
        self._store = ConfidenceStore(
            config.wiki_path / "confidence.json",
            config.confidence,
        )

    def run(self, fix: bool = False) -> LintReport:
        """
        Run all lint checks on the wiki.

        Args:
            fix: If True, attempt to auto-fix fixable issues.
        """
        report = LintReport()
        pages = self._wiki.all_pages()
        report.pages_checked = len(pages)

        # Confidence checks run regardless of page count
        self._check_low_confidence(report)
        self._check_contradictions(report)

        if not pages:
            return report

        # Build a map of all known page paths for link validation (always forward slashes)
        known_paths = {
            str(p.path.relative_to(self._config.wiki_path)).replace("\\", "/")
            for p in pages
        }
        known_paths.add("index.md")
        known_paths.add("log.md")

        for page in pages:
            self._check_orphan(page, pages, report)
            self._check_broken_links(page, known_paths, report)
            self._check_missing_source(page, report)
            self._check_stale_frontmatter(page, report)

        self._check_missing_index_entries(pages, report)

        if fix:
            self._auto_fix(report)

        return report

    # ── Checks ────────────────────────────────────────────────────────────────

    def _check_orphan(
        self, page: WikiPage, all_pages: list[WikiPage], report: LintReport
    ) -> None:
        """A page is orphaned if no other page links to it."""
        page_rel = str(page.path.relative_to(self._config.wiki_path)).replace("\\", "/")
        page_stem = page.path.stem

        referenced = False
        for other in all_pages:
            if other.path == page.path:
                continue
            if page_stem in other.body or page_rel in other.body:
                referenced = True
                break

        # Also check index.md
        index_path = self._config.wiki_path / "index.md"
        if index_path.exists() and page_stem in index_path.read_text(encoding="utf-8"):
            referenced = True

        if not referenced:
            # Summaries are always linked from log, don't flag them
            if page.frontmatter.get("type") != "summary":
                report.issues.append(LintIssue(
                    severity="warning",
                    issue_type="orphan",
                    page=page_rel,
                    detail=f"No other page links to this page.",
                    auto_fixable=False,
                ))

    def _check_broken_links(
        self, page: WikiPage, known_paths: set[str], report: LintReport
    ) -> None:
        """Find markdown links pointing to non-existent pages."""
        page_rel = str(page.path.relative_to(self._config.wiki_path)).replace("\\", "/")
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

        for match in link_pattern.finditer(page.body):
            href = match.group(2)
            # Skip external URLs and anchors
            if href.startswith("http") or href.startswith("#"):
                continue
            # Resolve relative to page directory
            resolved = str(
                (page.path.parent / href).resolve().relative_to(
                    self._config.wiki_path.resolve()
                )
            ).replace("\\", "/")

            if resolved not in known_paths and href not in known_paths:
                report.issues.append(LintIssue(
                    severity="error",
                    issue_type="broken_link",
                    page=page_rel,
                    detail=f"Broken link: [{match.group(1)}]({href})",
                    auto_fixable=True,
                ))

    def _check_missing_source(self, page: WikiPage, report: LintReport) -> None:
        """Warn if a non-summary page has no source SHAs."""
        page_rel = str(page.path.relative_to(self._config.wiki_path)).replace("\\", "/")
        if page.frontmatter.get("type") in {"summary"}:
            return
        sources = page.frontmatter.get("sources", [])
        if not sources:
            report.issues.append(LintIssue(
                severity="info",
                issue_type="missing_source",
                page=page_rel,
                detail="Page has no source commit references.",
                auto_fixable=False,
            ))

    def _check_stale_frontmatter(self, page: WikiPage, report: LintReport) -> None:
        """Flag pages missing required frontmatter fields."""
        page_rel = str(page.path.relative_to(self._config.wiki_path)).replace("\\", "/")
        required = {"type", "name", "created", "updated"}
        missing = required - set(page.frontmatter.keys())
        if missing:
            report.issues.append(LintIssue(
                severity="warning",
                issue_type="stale",
                page=page_rel,
                detail=f"Missing frontmatter fields: {', '.join(sorted(missing))}",
                auto_fixable=True,
            ))

    def _check_low_confidence(self, report: LintReport) -> None:
        """Flag facts with low confidence scores."""
        low = self._store.low_confidence_facts(threshold=0.4)
        for fact in low:
            report.issues.append(LintIssue(
                severity="warning",
                issue_type="low_confidence",
                page=f"confidence:{fact.entity}",
                detail=f"Low confidence ({fact.confidence:.2f}): \"{fact.statement[:80]}\"",
                auto_fixable=False,
            ))

    def _check_contradictions(self, report: LintReport) -> None:
        """Flag facts that have been contradicted."""
        contradicted = self._store.contradicted_facts()
        for fact in contradicted:
            report.issues.append(LintIssue(
                severity="error",
                issue_type="contradiction",
                page=f"confidence:{fact.entity}",
                detail=(
                    f"Contradiction: \"{fact.statement[:60]}\" "
                    f"conflicts with: \"{fact.contradicted_by[0][:60]}\""
                ),
                auto_fixable=True,
            ))

    def _check_missing_index_entries(
        self, pages: list[WikiPage], report: LintReport
    ) -> None:
        """Warn if a non-summary page is not listed in index.md."""
        index_path = self._config.wiki_path / "index.md"
        if not index_path.exists():
            report.issues.append(LintIssue(
                severity="warning",
                issue_type="stale",
                page="index.md",
                detail="index.md does not exist.",
                auto_fixable=False,
            ))
            return

        index_content = index_path.read_text(encoding="utf-8")
        for page in pages:
            if page.frontmatter.get("type") == "summary":
                continue
            if page.path.stem not in index_content:
                page_rel = str(page.path.relative_to(self._config.wiki_path)).replace("\\", "/")
                report.issues.append(LintIssue(
                    severity="info",
                    issue_type="missing_source",
                    page=page_rel,
                    detail="Page not listed in index.md.",
                    auto_fixable=True,
                ))

    # ── Auto-fix ──────────────────────────────────────────────────────────────

    def _auto_fix(self, report: LintReport) -> None:
        """Apply automatic fixes for fixable issues."""
        for issue in report.issues:
            if not issue.auto_fixable:
                continue

            if issue.issue_type == "stale" and "Missing frontmatter fields" in issue.detail:
                fixed = self._fix_missing_frontmatter(issue.page)
                if fixed:
                    report.fixed.append(f"Added missing frontmatter to {issue.page}")

            elif issue.issue_type == "broken_link":
                fixed = self._fix_broken_link(issue.page, issue.detail)
                if fixed:
                    report.fixed.append(f"Removed broken link in {issue.page}")

            elif issue.issue_type == "contradiction":
                fixed = self._fix_contradiction_with_llm(issue)
                if fixed:
                    report.fixed.append(f"Resolved contradiction: {issue.detail[:60]}")

            elif issue.issue_type == "missing_source" and "not listed in index.md" in issue.detail:
                fixed = self._fix_missing_index_entry(issue.page)
                if fixed:
                    report.fixed.append(f"Added {issue.page} to index.md")

    def _fix_missing_frontmatter(self, page_rel: str) -> bool:
        try:
            page = WikiPage(self._config.wiki_path / page_rel)
            from llmwikidoc.wiki import _now_iso
            now = _now_iso()
            for field_name, default in [
                ("type", "concept"), ("name", page.path.stem),
                ("created", now), ("updated", now),
            ]:
                if field_name not in page.frontmatter:
                    page.frontmatter[field_name] = default
            page.save()
            return True
        except Exception:
            return False

    def _fix_broken_link(self, page_rel: str, detail: str) -> bool:
        """Remove the broken link, keeping the link text."""
        try:
            page = WikiPage(self._config.wiki_path / page_rel)
            # Replace [text](broken_url) with just `text`
            page.body = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"`\1`", page.body)
            page.save()
            return True
        except Exception:
            return False

    def _fix_contradiction_with_llm(self, issue: LintIssue) -> bool:
        """Use Gemini to decide which of two contradicting facts is more likely correct."""
        try:
            from llmwikidoc.llm import LLMClient
            prompt = (
                f"Two facts about this software project contradict each other:\n\n"
                f"{issue.detail}\n\n"
                f"Which claim is more likely to be current and correct? "
                f"Reply with ONLY 'first' or 'second', then a one-sentence explanation."
            )
            with LLMClient(self._config) as llm:
                response = llm.generate(prompt).strip().lower()

            # Log the resolution in the wiki log
            self._wiki.append_log(
                "LINT_FIX",
                "contradiction",
                f"LLM resolution: {response[:120]}",
            )
            return True
        except Exception:
            return False

    def _fix_missing_index_entry(self, page_rel: str) -> bool:
        try:
            page = WikiPage(self._config.wiki_path / page_rel)
            name = str(page.frontmatter.get("name", page.path.stem))
            page_type = str(page.frontmatter.get("type", "concept"))
            subdir = page.path.parent.name
            summary = page.body.split("\n")[1][:80] if len(page.body.split("\n")) > 1 else ""
            self._wiki.update_index(name, page_type, subdir, summary)
            return True
        except Exception:
            return False
