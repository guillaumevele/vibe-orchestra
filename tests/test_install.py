"""Tests for the TOML surgery that wires mcp_servers. Needs tomllib (3.11+)."""
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.version_info < (3, 11),
                                reason="install needs tomllib (3.11+)")

try:
    import tomllib  # noqa: E402
except ModuleNotFoundError:
    tomllib = None

from vibe_orchestra import install as I  # noqa: E402


def _names(text):
    return [s["name"] for s in tomllib.loads(text)["mcp_servers"]]


def test_patch_empty_config():
    out = I.patch_mcp_servers("", I.OUR_SERVERS)
    assert _names(out) == ["vibe-orchestra", "vibe-fim"]


def test_existing_empty_inline_array_preserves_other_keys():
    text = 'active_model = "x"\nmcp_servers = []\n\n[tools.bash]\ndefault_timeout = 1200\n'
    out = I.patch_mcp_servers(text, I.OUR_SERVERS)
    d = tomllib.loads(out)
    assert len(d["mcp_servers"]) == 2
    assert d["active_model"] == "x"
    assert d["tools"]["bash"]["default_timeout"] == 1200  # untouched


def test_idempotent_no_duplicates():
    text = 'mcp_servers = []\n[a]\nb = 1\n'
    once = I.patch_mcp_servers(text, I.OUR_SERVERS)
    twice = I.patch_mcp_servers(once, I.OUR_SERVERS)
    assert _names(twice) == ["vibe-orchestra", "vibe-fim"]


def test_preserves_a_user_server():
    text = 'mcp_servers = [ { name = "mine", transport = "stdio", command = "x" } ]\n[a]\nb=1\n'
    out = I.patch_mcp_servers(text, I.OUR_SERVERS)
    names = _names(out)
    assert "mine" in names and "vibe-fim" in names and len(names) == 3


def test_uninstall_removes_ours_keeps_user():
    text = 'mcp_servers = [ { name = "mine", transport = "stdio", command = "x" } ]\n'
    installed = I.patch_mcp_servers(text, I.OUR_SERVERS)
    removed = I.patch_mcp_servers(installed, [])
    assert _names(removed) == ["mine"]


def test_double_bracket_blocks_are_normalised():
    text = ('active_model = "x"\n[[mcp_servers]]\nname = "mine"\ntransport = "stdio"\n'
            'command = "c"\n\n[tools.bash]\ndefault_timeout = 1200\n')
    out = I.patch_mcp_servers(text, I.OUR_SERVERS)
    d = tomllib.loads(out)
    assert "mine" in _names(out) and len(d["mcp_servers"]) == 3
    assert d["tools"]["bash"]["default_timeout"] == 1200


def test_marker_block_roundtrip():
    base = "# my notes\n"
    withp = I._set_marker_block(base, I.POSTURE_MARK, "POSTURE BODY")
    assert "POSTURE BODY" in withp and base in withp
    stripped = I._strip_marker_block(withp, I.POSTURE_MARK)
    assert "POSTURE BODY" not in stripped and "my notes" in stripped
