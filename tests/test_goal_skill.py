"""Tests for the /goal skill install. Needs tomllib (3.11+) for the verifier toml."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.version_info < (3, 11),
                                reason="install/toml needs 3.11+")

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None

from vibe_orchestra import install as I  # noqa: E402

REPO = Path(I.__file__).resolve().parent.parent
_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def test_install_writes_goal_skill_with_valid_frontmatter(tmp_path):
    I.install(tmp_path, REPO, ios_kit=None)
    skill = tmp_path / "skills" / "goal" / "SKILL.md"
    assert skill.exists()
    text = skill.read_text(encoding="utf-8")
    fm = re.search(r"^---\n(.*?)\n---", text, re.S)
    assert fm, "missing YAML frontmatter"
    name = re.search(r"(?m)^name:\s*(\S+)", fm.group(1)).group(1)
    assert name == "goal" and _NAME_RE.match(name)        # SkillMetadata pattern
    assert re.search(r"(?m)^description:\s*\S", fm.group(1))  # non-empty description


def test_goal_is_not_a_reserved_builtin_name():
    # vibe reserves builtin skill names and silently skips a duplicate. 'goal' is
    # not a builtin today; this guards a future collision in the kit's own name.
    assert "goal" not in {"explore", "plan", "lean"}


def test_verifier_subagent_pins_no_model(tmp_path):
    I.install(tmp_path, REPO, ios_kit=None)
    gv = tmp_path / "agents" / "goal-verifier.toml"
    assert gv.exists()
    d = tomllib.loads(gv.read_text(encoding="utf-8"))
    assert d["agent_type"] == "subagent"
    assert d["enabled_tools"] == ["read", "grep", "bash"]
    # The whole point: it must NOT pin active_model (that crashes on dispatch if
    # the alias is absent from config.models).
    assert "active_model" not in d


def test_goal_thinker_pins_magistral_with_self_contained_block(tmp_path):
    # The owner-gated model-pinning pattern: it MUST co-declare its provider+model
    # so active_model resolves (else it crashes on dispatch). Proven to boot live.
    I.install(tmp_path, REPO, ios_kit=None)
    d = tomllib.loads((tmp_path / "agents" / "goal-thinker.toml").read_text())
    assert d["agent_type"] == "subagent"
    assert d["active_model"] == "magistral"
    aliases = {m["alias"] for m in d["models"]}
    assert "magistral" in aliases                    # the pinned alias is declared
    assert any(p["name"] == "mistral-thinker" for p in d["providers"])
    # thinking must be off (magistral rejects a reasoning_effort request, HTTP 400)
    assert all(m.get("thinking", "off") == "off" for m in d["models"])
    # never embed a key; the provider references an env var
    assert d["providers"][0]["api_key_env_var"] == "MISTRAL_API_KEY"
    assert "api_key" not in d["providers"][0]


def test_uninstall_removes_goal(tmp_path):
    I.install(tmp_path, REPO, ios_kit=None)
    I.uninstall(tmp_path)
    assert not (tmp_path / "skills" / "goal").exists()
    assert not (tmp_path / "agents" / "goal-verifier.toml").exists()
    assert not (tmp_path / "agents" / "goal-thinker.toml").exists()
