"""Tests for lint.py — orphans, broken links, missing frontmatter, contradictions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from llmwikidoc.config import Config
from llmwikidoc.lint import WikiLinter, LintReport
from llmwikidoc.wiki import WikiManager
from llmwikidoc.confidence import ConfidenceStore


def make_healthy_wiki(wiki_path: Path) -> WikiManager:
    """Create a minimal healthy wiki for baseline tests."""
    wiki = WikiManager(wiki_path)
    wiki.create_or_update_page(
        "entities", "UserService",
        "# UserService\n\nHandles authentication.\n\nSee also [Authentication](../concepts/authentication.md).",
        page_type="class", sources=["sha1"],
    )
    wiki.create_or_update_page(
        "concepts", "Authentication",
        "# Authentication\n\nJWT-based auth used by [UserService](../entities/userservice.md).",
        page_type="concept", sources=["sha1"],
    )
    wiki.update_index("UserService", "class", "entities", "Handles authentication")
    wiki.update_index("Authentication", "concept", "concepts", "JWT-based auth")
    return wiki


# ── Basic lint ────────────────────────────────────────────────────────────────

def test_lint_healthy_wiki(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)
    make_healthy_wiki(config.wiki_path)

    linter = WikiLinter(config)
    report = linter.run()

    # A healthy wiki should have no errors
    assert len(report.errors) == 0
    assert report.pages_checked == 2


def test_lint_empty_wiki(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)
    from llmwikidoc.wiki import WikiManager
    WikiManager(config.wiki_path)

    linter = WikiLinter(config)
    report = linter.run()
    assert report.pages_checked == 0
    assert report.issues == []


# ── Orphan detection ──────────────────────────────────────────────────────────

def test_lint_detects_orphan(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)
    wiki = WikiManager(config.wiki_path)

    # Create a page with no links pointing to it
    wiki.create_or_update_page(
        "entities", "OrphanClass",
        "# OrphanClass\n\nNobody links here.",
        page_type="class", sources=["sha1"],
    )

    linter = WikiLinter(config)
    report = linter.run()

    orphan_issues = [i for i in report.issues if i.issue_type == "orphan"]
    assert len(orphan_issues) >= 1
    assert any("orphan" in i.issue_type for i in orphan_issues)


# ── Broken link detection ─────────────────────────────────────────────────────

def test_lint_detects_broken_link(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)
    wiki = WikiManager(config.wiki_path)

    wiki.create_or_update_page(
        "entities", "BrokenLinker",
        "# BrokenLinker\n\nSee [NonExistent](../concepts/does_not_exist.md).",
        page_type="class", sources=["sha1"],
    )

    linter = WikiLinter(config)
    report = linter.run()

    broken = [i for i in report.issues if i.issue_type == "broken_link"]
    assert len(broken) >= 1
    assert any("does_not_exist" in i.detail for i in broken)


# ── Missing frontmatter ───────────────────────────────────────────────────────

def test_lint_detects_missing_frontmatter(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)

    # Write a page with no frontmatter at all
    (config.wiki_path / "entities").mkdir(parents=True, exist_ok=True)
    (config.wiki_path / "entities" / "raw_page.md").write_text(
        "# Raw Page\n\nNo frontmatter here.", encoding="utf-8"
    )

    linter = WikiLinter(config)
    report = linter.run()

    stale = [i for i in report.issues if i.issue_type == "stale" and "frontmatter" in i.detail]
    assert len(stale) >= 1


# ── Auto-fix ──────────────────────────────────────────────────────────────────

def test_lint_fix_missing_frontmatter(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)

    (config.wiki_path / "entities").mkdir(parents=True, exist_ok=True)
    page_path = config.wiki_path / "entities" / "fixme.md"
    page_path.write_text("# FixMe\n\nNeeds frontmatter.", encoding="utf-8")

    linter = WikiLinter(config)
    report = linter.run(fix=True)

    # After fix, the page should have frontmatter
    content = page_path.read_text(encoding="utf-8")
    assert "---" in content
    assert "type:" in content


def test_lint_fix_broken_link(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)
    wiki = WikiManager(config.wiki_path)

    wiki.create_or_update_page(
        "entities", "LinkPage",
        "# LinkPage\n\nSee [Missing](../concepts/gone.md) for details.",
        page_type="class", sources=["sha1"],
    )

    linter = WikiLinter(config)
    report = linter.run(fix=True)

    # After fix, the broken link should be replaced with inline code
    page_path = config.wiki_path / "entities" / "linkpage.md"
    content = page_path.read_text(encoding="utf-8")
    assert "gone.md" not in content
    assert "`Missing`" in content


# ── Contradiction detection ───────────────────────────────────────────────────

def test_lint_detects_contradictions(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)
    WikiManager(config.wiki_path)

    store = ConfidenceStore(config.wiki_path / "confidence.json", config.confidence)
    store.add_fact("UserService uses Redis", "UserService", "sha1")
    store.contradict("UserService", "UserService uses Redis", "UserService uses Memcached")
    store.save()

    linter = WikiLinter(config)
    report = linter.run()

    contradiction_issues = [i for i in report.issues if i.issue_type == "contradiction"]
    assert len(contradiction_issues) >= 1


# ── Low confidence detection ──────────────────────────────────────────────────

def test_lint_detects_low_confidence(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)
    WikiManager(config.wiki_path)

    store = ConfidenceStore(config.wiki_path / "confidence.json", config.confidence)
    store.add_fact("Some uncertain claim", "Entity", "sha1")
    # Force confidence very low
    key = list(store._facts.keys())[0]
    store._facts[key].confidence = 0.2
    store.save()

    linter = WikiLinter(config)
    report = linter.run()

    low_conf = [i for i in report.issues if i.issue_type == "low_confidence"]
    assert len(low_conf) >= 1


# ── Report ────────────────────────────────────────────────────────────────────

def test_lint_report_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = Config(project_root=tmp_path)
    WikiManager(config.wiki_path)

    linter = WikiLinter(config)
    report = linter.run()
    summary = report.summary()
    assert "pages checked" in summary
    assert "errors" in summary
