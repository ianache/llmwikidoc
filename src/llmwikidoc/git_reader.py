"""Extract full context from a git commit: message, diff, file contents, related files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import git


@dataclass
class CommitContext:
    sha: str
    short_sha: str
    message: str
    author: str
    timestamp: str                          # ISO-8601
    diff: str                               # full unified diff
    changed_files: list[str]               # relative paths
    file_contents: dict[str, str]          # path -> full content (modified files)
    related_files: dict[str, str]          # path -> full content (imports/callers)
    stats: dict[str, dict[str, int]]       # path -> {insertions, deletions}


def read_commit(
    repo_path: Path,
    sha: str | None = None,
    context_depth: int = 2,
) -> CommitContext:
    """
    Read a commit and gather full context.

    Args:
        repo_path: Root of the git repository.
        sha: Commit SHA to read. Defaults to HEAD.
        context_depth: How many levels of related files to follow (imports, callers).
    """
    repo = git.Repo(str(repo_path))
    commit = repo.commit(sha) if sha else repo.head.commit

    # Basic metadata
    short_sha = commit.hexsha[:8]
    message = commit.message.strip()
    author = f"{commit.author.name} <{commit.author.email}>"
    timestamp = commit.authored_datetime.isoformat()

    # Diff
    if commit.parents:
        diff_str = repo.git.diff(commit.parents[0].hexsha, commit.hexsha)
        raw_diffs = commit.diff(commit.parents[0])
    else:
        # Initial commit: diff against empty tree
        diff_str = repo.git.show(commit.hexsha, format="", name_only=True)
        raw_diffs = commit.diff(git.NULL_TREE)

    # Changed files and stats
    changed_files: list[str] = []
    stats: dict[str, dict[str, int]] = {}
    for d in raw_diffs:
        path = d.b_path or d.a_path
        if path:
            changed_files.append(path)

    for path, file_stats in commit.stats.files.items():
        stats[path] = {
            "insertions": file_stats.get("insertions", 0),
            "deletions": file_stats.get("deletions", 0),
        }

    # Full content of modified files (at HEAD state)
    file_contents: dict[str, str] = {}
    for path in changed_files:
        content = _read_file_at_commit(repo, commit, path)
        if content is not None:
            file_contents[path] = content

    # Related files (imports/dependencies)
    related_files: dict[str, str] = {}
    if context_depth > 0:
        related_paths = _find_related_files(
            repo_path, changed_files, file_contents, depth=context_depth
        )
        for path in related_paths:
            if path not in file_contents:
                content = _read_file_at_commit(repo, commit, path)
                if content is not None:
                    related_files[path] = content

    return CommitContext(
        sha=commit.hexsha,
        short_sha=short_sha,
        message=message,
        author=author,
        timestamp=timestamp,
        diff=diff_str,
        changed_files=changed_files,
        file_contents=file_contents,
        related_files=related_files,
        stats=stats,
    )


def _read_file_at_commit(
    repo: git.Repo, commit: git.Commit, path: str
) -> str | None:
    """Read file content as it exists in the given commit."""
    try:
        blob = commit.tree[path]
        return blob.data_stream.read().decode("utf-8", errors="replace")
    except (KeyError, Exception):
        return None


def _find_related_files(
    repo_path: Path,
    changed_files: list[str],
    file_contents: dict[str, str],
    depth: int,
) -> list[str]:
    """
    Find files related to the changed files by scanning imports/references.
    Supports Python, TypeScript/JavaScript, and Go.
    """
    related: set[str] = set()
    to_scan = list(changed_files)

    for _ in range(depth):
        next_scan: list[str] = []
        for file_path in to_scan:
            content = file_contents.get(file_path, "")
            if not content:
                # Try reading from disk
                full_path = repo_path / file_path
                if full_path.exists():
                    content = full_path.read_text(encoding="utf-8", errors="replace")

            imports = _extract_imports(file_path, content, repo_path)
            for imp in imports:
                if imp not in related and imp not in changed_files:
                    related.add(imp)
                    next_scan.append(imp)
        to_scan = next_scan

    return list(related)


def _extract_imports(file_path: str, content: str, repo_path: Path) -> list[str]:
    """Extract referenced local files from source code."""
    ext = Path(file_path).suffix.lower()
    base_dir = (repo_path / file_path).parent

    if ext == ".py":
        return _python_imports(content, base_dir, repo_path)
    elif ext in {".ts", ".tsx", ".js", ".jsx"}:
        return _js_imports(content, base_dir, repo_path)
    elif ext == ".go":
        return _go_imports(content, base_dir, repo_path)
    return []


def _python_imports(content: str, base_dir: Path, repo_path: Path) -> list[str]:
    """Resolve relative Python imports to file paths."""
    results: list[str] = []
    # Match: from .foo import bar  OR  from foo.bar import baz
    pattern = re.compile(r"^(?:from|import)\s+(\.+[\w.]*|[\w]+(?:\.[\w]+)*)", re.MULTILINE)
    for match in pattern.finditer(content):
        module = match.group(1)
        if module.startswith("."):
            # Relative import
            dots = len(module) - len(module.lstrip("."))
            module_path = module.lstrip(".")
            candidate_dir = base_dir
            for _ in range(dots - 1):
                candidate_dir = candidate_dir.parent
            if module_path:
                candidate = candidate_dir / module_path.replace(".", "/")
            else:
                candidate = candidate_dir
            for suffix in [".py", "/__init__.py"]:
                full = Path(str(candidate) + suffix)
                if full.exists():
                    try:
                        results.append(str(full.relative_to(repo_path)).replace("\\", "/"))
                    except ValueError:
                        pass
                    break
    return results


def _js_imports(content: str, base_dir: Path, repo_path: Path) -> list[str]:
    """Resolve relative JS/TS imports."""
    results: list[str] = []
    pattern = re.compile(r"""(?:import|from|require)\s*[('"](\.[^'"]+)['"')]""")
    for match in pattern.finditer(content):
        raw = match.group(1)
        candidate = (base_dir / raw).resolve()
        for suffix in ["", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js"]:
            full = Path(str(candidate) + suffix)
            if full.exists():
                try:
                    results.append(str(full.relative_to(repo_path)).replace("\\", "/"))
                except ValueError:
                    pass
                break
    return results


def _go_imports(content: str, base_dir: Path, repo_path: Path) -> list[str]:
    """Best-effort: find local Go files in the same package directory."""
    results: list[str] = []
    if not base_dir.exists():
        return results
    for go_file in base_dir.glob("*.go"):
        try:
            results.append(str(go_file.relative_to(repo_path)).replace("\\", "/"))
        except ValueError:
            pass
    return results
