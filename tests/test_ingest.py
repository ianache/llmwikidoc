"""Tests for ingest.py — uses mock LLM to avoid real API calls."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from llmwikidoc.config import Config
from llmwikidoc.git_reader import CommitContext
from llmwikidoc.ingest import ingest_commit, _build_extraction_prompt, _format_file_contents


MOCK_EXTRACTION = {
    "summary": "Add UserService for authentication",
    "entities": [
        {"name": "UserService", "type": "class", "description": "Handles user authentication"},
        {"name": "authenticate", "type": "function", "description": "Verifies user credentials"},
    ],
    "relations": [
        {"from": "UserService", "to": "Database", "type": "depends_on"},
    ],
    "facts": [
        {"statement": "UserService uses JWT tokens for auth", "entity": "UserService", "confidence": 0.8},
    ],
    "contradictions": [],
}


def make_mock_commit() -> CommitContext:
    return CommitContext(
        sha="abc123def456abc123def456abc123def456abc1",
        short_sha="abc123de",
        message="Add UserService for authentication",
        author="Test User <test@example.com>",
        timestamp="2026-04-29T12:00:00+00:00",
        diff="--- a/user_service.py\n+++ b/user_service.py\n@@ -0,0 +1,5 @@\n+class UserService:\n+    pass\n",
        changed_files=["user_service.py"],
        file_contents={"user_service.py": "class UserService:\n    pass\n"},
        related_files={},
        stats={"user_service.py": {"insertions": 5, "deletions": 0}},
    )


@patch("llmwikidoc.ingest.read_commit")
@patch("llmwikidoc.ingest.LLMClient")
def test_ingest_creates_pages(mock_llm_cls, mock_read_commit, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_read_commit.return_value = make_mock_commit()
    mock_llm = MagicMock()
    mock_llm.__enter__ = MagicMock(return_value=mock_llm)
    mock_llm.__exit__ = MagicMock(return_value=False)
    mock_llm.generate_structured.return_value = MOCK_EXTRACTION
    mock_llm_cls.return_value = mock_llm

    config = Config(project_root=tmp_path)
    result = ingest_commit(config)

    assert result.short_sha == "abc123de"
    assert len(result.pages_created) >= 1  # at least the summary
    assert result.entities_found == 2
    assert result.facts_added == 1
    assert result.contradictions == 0
    assert result.errors == []


@patch("llmwikidoc.ingest.read_commit")
@patch("llmwikidoc.ingest.LLMClient")
def test_ingest_updates_graph(mock_llm_cls, mock_read_commit, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_read_commit.return_value = make_mock_commit()
    mock_llm = MagicMock()
    mock_llm.__enter__ = MagicMock(return_value=mock_llm)
    mock_llm.__exit__ = MagicMock(return_value=False)
    mock_llm.generate_structured.return_value = MOCK_EXTRACTION
    mock_llm_cls.return_value = mock_llm

    config = Config(project_root=tmp_path)
    ingest_commit(config)

    from llmwikidoc.graph import KnowledgeGraph
    graph = KnowledgeGraph(config.wiki_path / "graph.json")
    assert "UserService" in graph.search_entities("UserService")
    assert graph.edge_count >= 1


@patch("llmwikidoc.ingest.read_commit")
@patch("llmwikidoc.ingest.LLMClient")
def test_ingest_logs_entry(mock_llm_cls, mock_read_commit, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_read_commit.return_value = make_mock_commit()
    mock_llm = MagicMock()
    mock_llm.__enter__ = MagicMock(return_value=mock_llm)
    mock_llm.__exit__ = MagicMock(return_value=False)
    mock_llm.generate_structured.return_value = MOCK_EXTRACTION
    mock_llm_cls.return_value = mock_llm

    config = Config(project_root=tmp_path)
    ingest_commit(config)

    log = (config.wiki_path / "log.md").read_text()
    assert "INGEST" in log
    assert "abc123de" in log


def test_build_extraction_prompt_contains_key_parts():
    ctx = make_mock_commit()
    prompt = _build_extraction_prompt(ctx)
    assert "UserService" in prompt
    assert ctx.message in prompt
    assert ctx.sha in prompt
    assert "JSON" in prompt


def test_format_file_contents_truncates():
    files = {"big_file.py": "x" * 10000}
    result = _format_file_contents(files, max_chars=100)
    assert len(result) < 300  # significantly truncated


def test_format_file_contents_empty():
    result = _format_file_contents({}, max_chars=1000)
    assert result == "(none)"
