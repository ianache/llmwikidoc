"""Tests for wiki.py."""

from pathlib import Path
from llmwikidoc.wiki import WikiManager, WikiPage, parse_frontmatter, render_frontmatter, _safe_filename


def test_parse_frontmatter_basic():
    content = "---\ntype: entity\nname: MyClass\nconfidence: 0.8\n---\n# Body\n"
    fm, body = parse_frontmatter(content)
    assert fm["type"] == "entity"
    assert fm["name"] == "MyClass"
    assert fm["confidence"] == 0.8
    assert body == "# Body\n"


def test_parse_frontmatter_no_frontmatter():
    content = "# Just a body\n"
    fm, body = parse_frontmatter(content)
    assert fm == {}
    assert body == "# Just a body\n"


def test_parse_frontmatter_list():
    content = "---\nsources: [sha1, sha2]\n---\nbody\n"
    fm, body = parse_frontmatter(content)
    assert fm["sources"] == ["sha1", "sha2"]


def test_render_frontmatter_roundtrip():
    fm = {"type": "entity", "name": "Foo", "confidence": 0.75, "sources": ["abc", "def"]}
    body = "# Foo\n\nSome content.\n"
    rendered = render_frontmatter(fm, body)
    fm2, body2 = parse_frontmatter(rendered)
    assert fm2["type"] == "entity"
    assert fm2["name"] == "Foo"
    assert abs(fm2["confidence"] - 0.75) < 0.01
    assert body2 == body


def test_safe_filename():
    assert _safe_filename("MyClass") == "myclass"
    assert _safe_filename("foo bar") == "foo_bar"
    assert _safe_filename("foo/bar.py") == "foobarpy"


def test_wiki_manager_creates_dirs(tmp_path):
    wiki = WikiManager(tmp_path / "wiki")
    assert (tmp_path / "wiki" / "entities").exists()
    assert (tmp_path / "wiki" / "concepts").exists()
    assert (tmp_path / "wiki" / "summaries").exists()


def test_create_page(tmp_path):
    wiki = WikiManager(tmp_path / "wiki")
    page = wiki.create_or_update_page(
        subdir="entities",
        name="UserService",
        body="# UserService\n\nHandles user auth.",
        page_type="class",
        sources=["abc123"],
        confidence=0.7,
    )
    assert page.path.exists()
    assert page.frontmatter["type"] == "class"
    assert page.frontmatter["confidence"] == 0.7


def test_update_page_bumps_confidence(tmp_path):
    wiki = WikiManager(tmp_path / "wiki")
    wiki.create_or_update_page(
        subdir="entities", name="Foo", body="# Foo\nFirst.", page_type="class",
        sources=["sha1"], confidence=0.7,
    )
    updated = wiki.create_or_update_page(
        subdir="entities", name="Foo", body="# Foo\nUpdated.", page_type="class",
        sources=["sha2"], confidence=0.7,
    )
    # Confidence should be bumped from 0.7
    assert updated.frontmatter["confidence"] > 0.7
    # Both sources should be present
    assert "sha1" in updated.frontmatter["sources"]
    assert "sha2" in updated.frontmatter["sources"]


def test_create_summary(tmp_path):
    wiki = WikiManager(tmp_path / "wiki")
    page = wiki.create_summary("abc12345", "# Summary\nDid X.", "abc12345abc12345")
    assert page.path.exists()
    assert page.frontmatter["type"] == "summary"


def test_append_log(tmp_path):
    wiki = WikiManager(tmp_path / "wiki")
    wiki.append_log("INGEST", "abc12345", "2 created, 1 updated")
    log = (tmp_path / "wiki" / "log.md").read_text()
    assert "INGEST" in log
    assert "abc1234" in log


def test_stats(tmp_path):
    wiki = WikiManager(tmp_path / "wiki")
    wiki.create_or_update_page("entities", "A", "body", page_type="class", sources=[])
    wiki.create_or_update_page("entities", "B", "body", page_type="function", sources=[])
    wiki.create_or_update_page("concepts", "C", "body", page_type="concept", sources=[])
    stats = wiki.stats()
    assert stats.get("class", 0) >= 1
    assert stats.get("concept", 0) >= 1
