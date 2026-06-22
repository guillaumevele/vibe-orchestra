"""Router tests. The classifier backend is injected — no network."""
from __future__ import annotations

import json

import pytest

from vibe_orchestra import ROUTES, RouterError, classify


def _fake(route: str, reason: str = "because"):
    return lambda system, user: json.dumps({"route": route, "reason": reason})


def test_each_route_maps_to_its_model():
    for name, route in ROUTES.items():
        d = classify("some task", chat_fn=_fake(name))
        # iOS override only fires for ios-flavoured build/edit tasks; "some task"
        # is neutral, so every route is preserved.
        assert d.route == name
        assert d.model == route.model


def test_surgical_edit_carries_the_fim_tool():
    d = classify("round computeScore to 2 decimals", chat_fn=_fake("surgical-edit"))
    assert d.route == "surgical-edit"
    assert d.tool == "vibe-fim_surgical_patch"
    assert d.model == "codestral-latest"


def test_ios_specialist_wins_over_generic_build_when_ios_content():
    # The model called it a build, but the task is clearly iOS/Metal.
    d = classify("add a shimmer Metal loader gated on scenePhase",
                 chat_fn=_fake("agentic-build"))
    assert d.route == "ios"
    assert d.specialist == "ios"
    assert "iOS" in d.reason


def test_ios_override_not_triggered_for_non_ios_build():
    d = classify("add a dark-mode theme to the web dashboard",
                 chat_fn=_fake("agentic-build"))
    assert d.route == "agentic-build"


def test_explicit_ios_route_is_kept():
    d = classify("build a SwiftUI settings screen", chat_fn=_fake("ios"))
    assert d.route == "ios"


def test_unrecognised_route_falls_back_to_chat():
    d = classify("whatever", chat_fn=lambda s, u: json.dumps({"route": "nonsense"}))
    assert d.route == "chat"
    assert "fell back" in d.reason


def test_malformed_classifier_output_falls_back():
    d = classify("whatever", chat_fn=lambda s, u: "not json at all")
    assert d.route == "chat"


def test_empty_task_raises():
    with pytest.raises(RouterError, match="empty task"):
        classify("   ", chat_fn=_fake("chat"))


def test_vision_route():
    d = classify("what's wrong with this screenshot?", chat_fn=_fake("vision"))
    assert d.route == "vision" and d.model == "pixtral-latest"
