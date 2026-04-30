"""Shared fixtures for all tests."""

from __future__ import annotations

import pytest
from pathlib import Path
from llmwikidoc.config import Config, ConfidenceConfig, SearchConfig


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """A temp directory with a .git folder (simulates a git project)."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "hooks").mkdir()
    return tmp_path


@pytest.fixture
def default_config(tmp_project: Path) -> Config:
    return Config(project_root=tmp_project)
