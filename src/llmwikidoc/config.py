"""Configuration management — reads/writes .llmwikidoc.toml in the project root."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

if __import__("sys").version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef]

import tomli_w  # will add to deps; use manual write for now

_CONFIG_FILENAME = ".llmwikidoc.toml"
_DEFAULT_WIKI_DIR = "wiki"
_DEFAULT_MODEL = "gemini-2.5-flash"


@dataclass
class ConfidenceConfig:
    initial: float = 0.7
    reinforce_delta: float = 0.1
    contradict_delta: float = -0.2
    decay_days: int = 30


@dataclass
class SearchConfig:
    bm25_weight: float = 0.33
    vector_weight: float = 0.33
    graph_weight: float = 0.34


@dataclass
class Config:
    model: str = _DEFAULT_MODEL
    wiki_dir: str = _DEFAULT_WIKI_DIR
    context_depth: int = 2
    confidence: ConfidenceConfig = field(default_factory=ConfidenceConfig)
    search: SearchConfig = field(default_factory=SearchConfig)

    # Runtime-only (not persisted)
    project_root: Path = field(default_factory=Path.cwd, repr=False)

    @property
    def api_key(self) -> str:
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key:
            raise EnvironmentError(
                "GEMINI_API_KEY environment variable is not set. "
                "Export it before running llmwikidoc."
            )
        return key

    @property
    def wiki_path(self) -> Path:
        return self.project_root / self.wiki_dir


def load(project_root: Path | None = None) -> Config:
    """Load config from .llmwikidoc.toml, falling back to defaults."""
    root = project_root or _find_project_root()
    config_file = root / _CONFIG_FILENAME

    cfg = Config(project_root=root)

    if not config_file.exists():
        return cfg

    with open(config_file, "rb") as f:
        data = tomllib.load(f)

    section = data.get("llmwikidoc", {})
    cfg.model = section.get("model", cfg.model)
    cfg.wiki_dir = section.get("wiki_dir", cfg.wiki_dir)
    cfg.context_depth = section.get("context_depth", cfg.context_depth)

    if conf_section := section.get("confidence", {}):
        cfg.confidence.initial = conf_section.get("initial", cfg.confidence.initial)
        cfg.confidence.reinforce_delta = conf_section.get("reinforce_delta", cfg.confidence.reinforce_delta)
        cfg.confidence.contradict_delta = conf_section.get("contradict_delta", cfg.confidence.contradict_delta)
        cfg.confidence.decay_days = conf_section.get("decay_days", cfg.confidence.decay_days)

    if search_section := section.get("search", {}):
        cfg.search.bm25_weight = search_section.get("bm25_weight", cfg.search.bm25_weight)
        cfg.search.vector_weight = search_section.get("vector_weight", cfg.search.vector_weight)
        cfg.search.graph_weight = search_section.get("graph_weight", cfg.search.graph_weight)

    return cfg


def write_default(project_root: Path) -> Path:
    """Write a default .llmwikidoc.toml to the given project root."""
    config_file = project_root / _CONFIG_FILENAME
    content = f"""\
[llmwikidoc]
model = "{_DEFAULT_MODEL}"
wiki_dir = "{_DEFAULT_WIKI_DIR}"
context_depth = 2

[llmwikidoc.confidence]
initial = 0.7
reinforce_delta = 0.1
contradict_delta = -0.2
decay_days = 30

[llmwikidoc.search]
bm25_weight = 0.33
vector_weight = 0.33
graph_weight = 0.34
"""
    config_file.write_text(content, encoding="utf-8")
    return config_file


def _find_project_root(start: Path | None = None) -> Path:
    """Walk up from start until we find a .git directory or filesystem root."""
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        if (directory / ".git").exists():
            return directory
    return current
