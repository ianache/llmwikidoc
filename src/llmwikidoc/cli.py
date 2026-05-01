"""CLI entry point — typer app with init, ingest, query, lint, status commands."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from llmwikidoc import __version__

app = typer.Typer(
    name="llmwikidoc",
    help="LLM-powered wiki that auto-updates from git commits.",
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)


# ── init ─────────────────────────────────────────────────────────────────────

@app.command()
def init(
    path: Annotated[
        Optional[Path],
        typer.Argument(help="Project root (defaults to current directory)"),
    ] = None,
) -> None:
    """Initialize llmwikidoc in a git project: create wiki/ and install the git hook."""
    from llmwikidoc import config as cfg_module
    from llmwikidoc.wiki import WikiManager

    project_root = (path or Path.cwd()).resolve()

    if not (project_root / ".git").exists():
        err_console.print(f"[red]Error:[/] No .git directory found in {project_root}")
        raise typer.Exit(1)

    config_file = cfg_module.write_default(project_root)
    console.print(f"[green]✓[/] Config written: {config_file.relative_to(project_root)}")

    config = cfg_module.load(project_root)
    WikiManager(config.wiki_path)
    console.print(f"[green]✓[/] Wiki initialized: {config.wiki_dir}/")

    _install_hook(project_root)

    console.print(Panel(
        f"[bold green]llmwikidoc initialized![/]\n\n"
        f"Set your API key:  [bold]export GEMINI_API_KEY=your_key[/]\n"
        f"Wiki directory:    [bold]{config.wiki_dir}/[/]\n"
        f"Config file:       [bold].llmwikidoc.toml[/]\n\n"
        f"The wiki will auto-update on every [bold]git commit[/].",
        title="Ready",
        border_style="green",
    ))


def _install_hook(project_root: Path) -> None:
    hooks_dir = project_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "post-commit"
    hook_content = _hook_script()

    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8")
        if "llmwikidoc" in existing:
            console.print("[yellow]⚠[/]  Hook already installed, skipping.")
            return
        hook_path.write_text(existing.rstrip() + "\n\n" + hook_content, encoding="utf-8")
        console.print("[green]✓[/] llmwikidoc appended to existing post-commit hook.")
    else:
        hook_path.write_text("#!/bin/sh\n\n" + hook_content, encoding="utf-8")
        import stat
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        console.print("[green]✓[/] post-commit hook installed.")


def _hook_script() -> str:
    return textwrap.dedent("""\
        # llmwikidoc — auto-update wiki on commit
        # Runs in background to avoid blocking the commit
        if command -v llmwikidoc >/dev/null 2>&1; then
            llmwikidoc ingest --quiet &
        fi
    """)


# ── ingest ────────────────────────────────────────────────────────────────────

@app.command()
def ingest(
    sha: Annotated[
        Optional[str],
        typer.Option("--sha", "-s", help="Commit SHA to ingest (defaults to HEAD)"),
    ] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q")] = False,
    all_commits: Annotated[
        bool,
        typer.Option("--all", help="Ingest all commits in history, excluding wiki/ content"),
    ] = False,
) -> None:
    """Ingest a commit and update the wiki."""
    from llmwikidoc import config as cfg_module
    from llmwikidoc.ingest import SkippedCommit, ingest_commit

    try:
        config = cfg_module.load()
    except Exception as exc:
        err_console.print(f"[red]Config error:[/] {exc}")
        raise typer.Exit(1)

    wiki_prefix = config.wiki_dir.rstrip("/") + "/"
    exclude = [wiki_prefix]

    if all_commits:
        _ingest_all(config, exclude, quiet)
        return

    if not quiet:
        console.print(f"[cyan]Ingesting commit...[/] (model: {config.model})")

    try:
        result = ingest_commit(config, sha=sha, exclude_prefixes=exclude)
    except SkippedCommit as exc:
        if not quiet:
            console.print(f"[yellow]Skipped:[/] {exc}")
        return
    except EnvironmentError as exc:
        err_console.print(f"[red]Error:[/] {exc}")
        raise typer.Exit(1)
    except Exception as exc:
        err_console.print(f"[red]Ingest failed:[/] {exc}")
        raise typer.Exit(1)

    if quiet:
        return

    _print_ingest_result(result)


def _ingest_all(config: object, exclude: list[str], quiet: bool) -> None:
    import git as _git
    from llmwikidoc.ingest import SkippedCommit, ingest_commit
    from llmwikidoc.wiki import WikiManager

    repo = _git.Repo(str(config.project_root))
    all_shas = [c.hexsha for c in repo.iter_commits(reverse=True)]

    # Determine already-ingested SHAs from existing summaries
    wiki = WikiManager(config.wiki_path)
    ingested = {p.stem for p in (config.wiki_path / "summaries").glob("*.md")} if (config.wiki_path / "summaries").exists() else set()

    pending = [s for s in all_shas if s[:8] not in ingested]

    if not pending:
        console.print("[green]All commits already ingested.[/]")
        return

    console.print(f"[cyan]Ingesting {len(pending)} commit(s) (skipping {len(ingested)} already done)...[/]")

    total_created = total_updated = total_facts = skipped = errors = 0

    for i, commit_sha in enumerate(pending, 1):
        short = commit_sha[:8]
        if not quiet:
            console.print(f"  [{i}/{len(pending)}] {short}", end=" ")
        try:
            result = ingest_commit(config, sha=commit_sha, exclude_prefixes=exclude)
            total_created += len(result.pages_created)
            total_updated += len(result.pages_updated)
            total_facts += result.facts_added
            if not quiet:
                console.print(f"[green]✓[/] +{len(result.pages_created)}p {result.facts_added}f")
        except SkippedCommit:
            skipped += 1
            if not quiet:
                console.print("[dim]skipped (wiki-only)[/]")
        except Exception as exc:
            errors += 1
            if not quiet:
                console.print(f"[red]error:[/] {exc}")

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_row("[green]Commits processed[/]", str(len(pending) - skipped - errors))
    table.add_row("[dim]Skipped (wiki-only)[/]", str(skipped))
    table.add_row("[green]Pages created[/]", str(total_created))
    table.add_row("[green]Pages updated[/]", str(total_updated))
    table.add_row("[green]Facts added[/]", str(total_facts))
    if errors:
        table.add_row("[red]Errors[/]", str(errors))
    console.print(Panel(table, title="Ingest all — complete", border_style="green"))


def _print_ingest_result(result: object) -> None:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_row("[green]Commit[/]", result.short_sha)
    table.add_row("[green]Pages created[/]", str(len(result.pages_created)))
    table.add_row("[green]Pages updated[/]", str(len(result.pages_updated)))
    table.add_row("[green]Entities found[/]", str(result.entities_found))
    table.add_row("[green]Facts added[/]", str(result.facts_added))
    if result.contradictions:
        table.add_row("[yellow]Contradictions[/]", str(result.contradictions))
    if result.errors:
        table.add_row("[red]Errors[/]", str(len(result.errors)))

    console.print(Panel(table, title=f"Ingest complete — {result.short_sha}", border_style="green"))

    if result.pages_created:
        console.print("[dim]Created:[/] " + ", ".join(result.pages_created[:5]))
    if result.pages_updated:
        console.print("[dim]Updated:[/] " + ", ".join(result.pages_updated[:5]))


# ── query ─────────────────────────────────────────────────────────────────────

@app.command()
def query(
    question: Annotated[str, typer.Argument(help="Question to ask about the project")],
    streams: Annotated[
        Optional[str],
        typer.Option("--streams", help="Search streams to use: bm25, vector, graph, all (default: all)"),
    ] = "all",
) -> None:
    """Query the wiki using hybrid search (BM25 + vector + graph)."""
    from llmwikidoc import config as cfg_module
    from llmwikidoc.llm import LLMClient
    from llmwikidoc.search import HybridSearch

    try:
        config = cfg_module.load()
    except Exception as exc:
        err_console.print(f"[red]Config error:[/] {exc}")
        raise typer.Exit(1)

    if not config.wiki_path.exists():
        err_console.print("[red]Wiki not initialized.[/] Run [bold]llmwikidoc init[/] first.")
        raise typer.Exit(1)

    console.print(f"[cyan]Searching wiki:[/] {question}")

    # Override search weights if specific streams requested
    if streams and streams != "all":
        active = {s.strip() for s in streams.split(",")}
        config.search.bm25_weight = 1.0 if "bm25" in active else 0.0
        config.search.vector_weight = 1.0 if "vector" in active else 0.0
        config.search.graph_weight = 1.0 if "graph" in active else 0.0

    searcher = HybridSearch(config)
    results = searcher.search(question, top_k=5)

    if not results:
        console.print("[yellow]No relevant pages found in wiki.[/]")
        raise typer.Exit(0)

    # Build context from search results
    context_parts: list[str] = []
    for r in results:
        context_parts.append(f"## {r.page.path.stem} (score: {r.score:.3f}, via: {', '.join(r.sources)})\n{r.page.body[:2000]}")
    context = "\n\n---\n\n".join(context_parts)

    prompt = (
        f"You are answering a question about a software project using its wiki documentation.\n\n"
        f"## Wiki Context\n\n{context}\n\n"
        f"## Question\n\n{question}\n\n"
        f"Answer concisely and cite the wiki pages you used."
    )

    with LLMClient(config) as llm:
        answer = llm.generate(prompt)

    console.print(Panel(answer, title="Answer", border_style="blue"))

    # Show which streams contributed to each result
    sources_table = Table(show_header=True, box=None)
    sources_table.add_column("Page", style="cyan")
    sources_table.add_column("Score", style="white")
    sources_table.add_column("Streams", style="dim")
    for r in results:
        sources_table.add_row(r.page.path.stem, f"{r.score:.3f}", ", ".join(r.sources))
    console.print(sources_table)


# ── lint ──────────────────────────────────────────────────────────────────────

@app.command()
def lint(
    fix: Annotated[bool, typer.Option("--fix", help="Auto-fix fixable issues")] = False,
) -> None:
    """Check wiki health: orphaned pages, broken links, contradictions, low confidence facts."""
    from llmwikidoc import config as cfg_module
    from llmwikidoc.lint import WikiLinter

    try:
        config = cfg_module.load()
    except Exception as exc:
        err_console.print(f"[red]Config error:[/] {exc}")
        raise typer.Exit(1)

    if not config.wiki_path.exists():
        err_console.print("[red]Wiki not initialized.[/] Run [bold]llmwikidoc init[/] first.")
        raise typer.Exit(1)

    console.print("[cyan]Running wiki health check...[/]")

    linter = WikiLinter(config)
    report = linter.run(fix=fix)

    # Print issues grouped by severity
    severity_styles = {"error": "red", "warning": "yellow", "info": "dim"}
    severity_icons = {"error": "✗", "warning": "⚠", "info": "ℹ"}

    if not report.issues:
        console.print(Panel(
            f"[green]Wiki is healthy![/] {report.summary()}",
            border_style="green",
        ))
        return

    table = Table(show_header=True, title=f"Lint Report — {report.summary()}")
    table.add_column("Sev", style="white", width=5)
    table.add_column("Type", style="cyan", width=18)
    table.add_column("Page", style="white", width=35)
    table.add_column("Detail", style="dim")

    for issue in sorted(report.issues, key=lambda i: ("error", "warning", "info").index(i.severity)):
        style = severity_styles[issue.severity]
        icon = severity_icons[issue.severity]
        table.add_row(
            f"[{style}]{icon}[/{style}]",
            issue.issue_type,
            issue.page[:35],
            issue.detail[:80],
        )

    console.print(table)

    if fix and report.fixed:
        console.print(f"\n[green]Auto-fixed {len(report.fixed)} issue(s):[/]")
        for fix_msg in report.fixed:
            console.print(f"  [green]✓[/] {fix_msg}")

    # Exit with error code if there are errors (useful for CI)
    if report.errors:
        raise typer.Exit(1)


# ── consolidate ──────────────────────────────────────────────────────────────

@app.command()
def consolidate() -> None:
    """Run consolidation cycle: apply Ebbinghaus decay and promote facts/pages across memory tiers."""
    from llmwikidoc import config as cfg_module
    from llmwikidoc.wiki import WikiManager
    from llmwikidoc.confidence import ConfidenceStore
    from llmwikidoc.consolidate import run_consolidation

    try:
        config = cfg_module.load()
    except Exception as exc:
        err_console.print(f"[red]Config error:[/] {exc}")
        raise typer.Exit(1)

    if not config.wiki_path.exists():
        err_console.print("[red]Wiki not initialized.[/] Run [bold]llmwikidoc init[/] first.")
        raise typer.Exit(1)

    wiki = WikiManager(config.wiki_path)
    store = ConfidenceStore(config.wiki_path / "confidence.json", config.confidence)

    console.print("[cyan]Running consolidation cycle...[/]")
    result = run_consolidation(wiki, store)

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_row("[green]Facts decayed[/]", str(result.facts_decayed))
    table.add_row("[green]Facts promoted[/]", str(result.facts_promoted))
    table.add_row("[green]Pages promoted[/]", str(result.pages_promoted))
    if result.pages_compressed:
        table.add_row("[green]Pages compressed[/]", str(len(result.pages_compressed)))
    if result.decay_warnings:
        table.add_row("[yellow]Low confidence facts[/]", str(len(result.decay_warnings)))
        for w in result.decay_warnings[:3]:
            console.print(f"  [yellow]⚠[/] {w}")

    console.print(Panel(table, title="Consolidation complete", border_style="green"))


# ── digest ────────────────────────────────────────────────────────────────────

@app.command()
def digest(
    n: Annotated[
        int,
        typer.Option("--n", "-n", help="Number of recent commits to include"),
    ] = 10,
) -> None:
    """Crystallize N recent commits into a semantic-tier digest page."""
    from llmwikidoc import config as cfg_module
    from llmwikidoc.wiki import WikiManager
    from llmwikidoc.confidence import ConfidenceStore
    from llmwikidoc.llm import LLMClient
    from llmwikidoc.consolidate import create_digest

    try:
        config = cfg_module.load()
    except Exception as exc:
        err_console.print(f"[red]Config error:[/] {exc}")
        raise typer.Exit(1)

    if not config.wiki_path.exists():
        err_console.print("[red]Wiki not initialized.[/] Run [bold]llmwikidoc init[/] first.")
        raise typer.Exit(1)

    console.print(f"[cyan]Creating digest from last {n} commits...[/]")

    wiki = WikiManager(config.wiki_path)
    store = ConfidenceStore(config.wiki_path / "confidence.json", config.confidence)

    try:
        with LLMClient(config) as llm:
            result = create_digest(wiki, store, llm, n_recent=n)
    except ValueError as exc:
        err_console.print(f"[red]Error:[/] {exc}")
        raise typer.Exit(1)
    except EnvironmentError as exc:
        err_console.print(f"[red]Error:[/] {exc}")
        raise typer.Exit(1)

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_row("[green]Digest page[/]", result.digest_page)
    table.add_row("[green]Commits covered[/]", str(result.commits_covered))
    table.add_row("[green]Entities mentioned[/]", str(result.entities_mentioned))
    table.add_row("[green]New facts extracted[/]", str(result.new_facts))

    console.print(Panel(table, title="Digest created", border_style="green"))
    console.print(f"[dim]wiki/concepts/{result.digest_page}.md[/]")


# ── status ────────────────────────────────────────────────────────────────────

@app.command()
def status() -> None:
    """Show wiki statistics."""
    from llmwikidoc import config as cfg_module
    from llmwikidoc.wiki import WikiManager
    from llmwikidoc.graph import KnowledgeGraph
    from llmwikidoc.confidence import ConfidenceStore

    try:
        config = cfg_module.load()
    except Exception as exc:
        err_console.print(f"[red]Config error:[/] {exc}")
        raise typer.Exit(1)

    if not config.wiki_path.exists():
        err_console.print("[red]Wiki not initialized.[/] Run [bold]llmwikidoc init[/] first.")
        raise typer.Exit(1)

    wiki = WikiManager(config.wiki_path)
    page_stats = wiki.stats()

    graph_path = config.wiki_path / "graph.json"
    graph = KnowledgeGraph(graph_path) if graph_path.exists() else None

    confidence_path = config.wiki_path / "confidence.json"
    store = ConfidenceStore(confidence_path, config.confidence) if confidence_path.exists() else None

    table = Table(title="Wiki Status", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    for page_type, count in sorted(page_stats.items()):
        table.add_row(f"Pages ({page_type})", str(count))

    if graph:
        table.add_row("Graph nodes", str(graph.node_count))
        table.add_row("Graph edges", str(graph.edge_count))

    if store:
        low_conf = store.low_confidence_facts(threshold=0.4)
        contradicted = store.contradicted_facts()
        table.add_row("Low confidence facts", str(len(low_conf)))
        table.add_row("Contradicted facts", str(len(contradicted)))

    table.add_row("Model", config.model)
    table.add_row("Wiki dir", str(config.wiki_path.relative_to(config.project_root)))

    console.print(table)


# ── version ───────────────────────────────────────────────────────────────────

@app.callback(invoke_without_command=True)
def main(
    version: Annotated[bool, typer.Option("--version", "-v")] = False,
    ctx: typer.Context = typer.Context,
) -> None:
    if version:
        console.print(f"llmwikidoc {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
