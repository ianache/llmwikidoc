"""Tests for config.py."""

from pathlib import Path
import pytest
from llmwikidoc.config import load, write_default, Config, _find_project_root


def test_default_config_values(tmp_project):
    cfg = Config(project_root=tmp_project)
    assert cfg.model == "gemini-2.5-flash"
    assert cfg.wiki_dir == "wiki"
    assert cfg.context_depth == 2
    assert cfg.confidence.initial == 0.7
    assert cfg.wiki_path == tmp_project / "wiki"


def test_write_and_load_config(tmp_project):
    config_file = write_default(tmp_project)
    assert config_file.exists()

    cfg = load(tmp_project)
    assert cfg.model == "gemini-2.5-flash"
    assert cfg.wiki_dir == "wiki"
    assert cfg.confidence.initial == 0.7


def test_load_custom_config(tmp_project):
    (tmp_project / ".llmwikidoc.toml").write_text(
        '[llmwikidoc]\nmodel = "gemini-2.5-pro"\nwiki_dir = "docs/wiki"\ncontext_depth = 3\n',
        encoding="utf-8",
    )
    cfg = load(tmp_project)
    assert cfg.model == "gemini-2.5-pro"
    assert cfg.wiki_dir == "docs/wiki"
    assert cfg.context_depth == 3


def test_api_key_missing_raises(tmp_project, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    cfg = Config(project_root=tmp_project)
    with pytest.raises(EnvironmentError, match="GEMINI_API_KEY"):
        _ = cfg.api_key


def test_api_key_from_env(tmp_project, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
    cfg = Config(project_root=tmp_project)
    assert cfg.api_key == "test-key-123"


def test_find_project_root_finds_git(tmp_project):
    subdir = tmp_project / "src" / "deep"
    subdir.mkdir(parents=True)
    root = _find_project_root(subdir)
    assert root == tmp_project
