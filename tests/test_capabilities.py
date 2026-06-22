"""Tests for subject detection, the catalog, and capability discovery."""
from __future__ import annotations

import json

from vibe_orchestra import recommend
from vibe_orchestra.catalog import CATALOG, capabilities_for, subjects_for


def _fake(route: str):
    return lambda system, user: json.dumps({"route": route, "reason": "x"})


def test_catalog_entries_are_well_formed():
    for c in CATALOG:
        assert c.id and c.kind in ("mcp", "skill", "tool") and c.command
        assert isinstance(c.subjects, tuple)


def test_ios_route_implies_ios_and_apple_docs_subjects():
    s = subjects_for("build a SwiftUI screen", "ios")
    assert "ios" in s and "apple-docs" in s


def test_keyword_subject_detection():
    assert "backend" in subjects_for("query the supabase database", "agentic-build")
    assert "vcs" in subjects_for("open a github pull request", "agentic-build")
    assert "web" in subjects_for("scrape this website", "agentic-build")
    assert "docs" in subjects_for("how to use the stripe library", "chat")


def test_capabilities_for_backend_returns_supabase():
    caps = capabilities_for(("backend",))
    assert any(c.id == "supabase" for c in caps)


def test_recommend_splits_use_and_add():
    # No vibe home -> nothing installed -> everything is "add".
    rec = recommend("build a SwiftUI Metal loader", chat_fn=_fake("ios"),
                    vibe_home="/nonexistent")
    ids = {c.id for c in rec["add"]}
    assert "apple-docs" in ids            # iOS subject -> apple-docs recommended
    assert rec["decision"].route == "ios"
    assert not rec["use"]                  # nothing wired in a nonexistent home


def test_keyed_capabilities_declare_their_env_var():
    keyed = {c.id: c.needs_key for c in CATALOG if c.needs_key}
    assert keyed.get("github") == "GITHUB_PERSONAL_ACCESS_TOKEN"
    assert keyed.get("supabase") == "SUPABASE_ACCESS_TOKEN"
