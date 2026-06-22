"""Wire vibe-orchestra into ~/.vibe, idempotently and reversibly.

The config edit is real TOML surgery: `mcp_servers` may already be declared (the
default config ships `mcp_servers = []`), and TOML forbids re-opening it with
`[[mcp_servers]]` after a table section. So we MERGE our servers into the existing
`mcp_servers` value (preserving any the user already has, by name) and render it as
a single inline array among the top-level keys.
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # install runs on the vibe machine (3.11+); kept import-safe

POSTURE_MARK = "vibe-orchestra"
OUR_SERVERS = [
    {"name": "vibe-orchestra", "transport": "stdio", "command": "vibe-orchestra-mcp",
     "startup_timeout_sec": 30.0,
     "prompt": "Call route(task) FIRST to pick the best Mistral model, specialist, tool, "
               "and the real plugins/skills to connect for the subject."},
    {"name": "vibe-fim", "transport": "stdio", "command": "vibe-fim-mcp",
     "startup_timeout_sec": 30.0,
     "prompt": "surgical_patch rewrites ONLY the region between two anchors via Codestral "
               "FIM; prefix/suffix byte-identical, rejected if it no longer parses."},
]
# Real, public, KEYLESS MCP servers connected with --with-capabilities. Verified
# npm packages; nothing here needs a secret. (Key-requiring servers — github,
# supabase, brave — are catalogued for the user to add themselves, never by us.)
# A generous startup timeout: a cold `npx -y` downloads the package on first run,
# which easily exceeds vibe's 10s default and would otherwise drop the server (and
# destabilise MCP init). install.sh also pre-warms the npm cache.
CAPABILITY_SERVERS = [
    {"name": "apple-docs", "transport": "stdio", "command": "npx",
     "args": ["-y", "@kimsungwhee/apple-docs-mcp"], "startup_timeout_sec": 90.0,
     "prompt": "Live Apple framework docs / WWDC / symbol search — verify iOS APIs."},
    {"name": "context7", "transport": "stdio", "command": "npx",
     "args": ["-y", "@upstash/context7-mcp"], "startup_timeout_sec": 90.0,
     "prompt": "Current docs for any library/framework by name."},
    {"name": "sequential-thinking", "transport": "stdio", "command": "npx",
     "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
     "startup_timeout_sec": 90.0,
     "prompt": "Structured multi-step reasoning scratchpad."},
]
# Everything we own (so --uninstall removes exactly these, preserving the user's).
OUR_NAMES = tuple(s["name"] for s in OUR_SERVERS + CAPABILITY_SERVERS)

_GOAL_VERIFIER = '''\
# Adversarial verifier subagent for /goal. The `task` tool can dispatch it
# (agent_type = subagent). It pins NO active_model -> inherits the session model
# -> boots safely. Read-only: it can run the proof command and read the diff, but
# it cannot edit, so it cannot fix-then-claim.
display_name = "Goal Verifier"
description = "Re-runs a /goal subtask's acceptance check independently. Read-only."
safety = "safe"
agent_type = "subagent"
enabled_tools = ["read", "grep", "bash"]
'''

_IOS_SKILL = """\
---
name: ios
description: iOS 26/27 build specialist. Use for any SwiftUI, Metal, Swift 6, or
  on-device FoundationModels task. Carries a CPU-budget posture and 38 distilled
  patterns, and edits Swift via bounded Codestral FIM.
---

# iOS specialist

When the task is iOS/SwiftUI/Metal work, follow this posture:

- Read `~/.vibe/orchestra/specialists/ios/AGENTS.md` (the build posture: CPU
  budget / gated animations, Swift 6 concurrency, native iOS 26 glass, on-device
  FoundationModels, premium no-emoji aesthetic, proof-not-vibes).
- Consult `~/.vibe/orchestra/specialists/ios/PATTERNS.md` (38 distilled iOS 26/27
  techniques) before building any non-trivial UI / shader / AI feature.
- Verify Apple APIs with the `apple-docs` plugin; do not trust memory.
- Edit a Swift file that already compiles with `vibe-fim_surgical_patch` (bounded
  region between two anchors) — never rewrite a working file to change a few lines.
- A change is done when it builds, the CPU-at-rest gate passes, reduced motion is
  handled, there are no emoji, and you have stated the proof you saw.
"""


def _toml_val(v) -> str:
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_val(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {_toml_val(x)}" for k, x in v.items()) + " }"
    return _toml_val(str(v))


def _render_mcp(servers: list[dict]) -> str:
    if not servers:
        return "mcp_servers = []  # vibe-orchestra-managed"
    rows = [
        "  { " + ", ".join(f"{k} = {_toml_val(v)}" for k, v in s.items()) + " },"
        for s in servers
    ]
    return "mcp_servers = [  # vibe-orchestra-managed\n" + "\n".join(rows) + "\n]"


def _inline_array_span(text: str, key: str):
    m = re.search(rf"(?m)^{re.escape(key)}\s*=\s*\[", text)
    if not m:
        return None
    i = text.index("[", m.start())
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "[":
            depth += 1
        elif text[j] == "]":
            depth -= 1
            if depth == 0:
                return (m.start(), j + 1)
    return None


def patch_mcp_servers(text: str, servers: list[dict]) -> str:
    """Merge `servers` (by name) into the config's mcp_servers and return new text.
    Pass servers=[] to remove ours while preserving any the user added."""
    try:
        existing = tomllib.loads(text).get("mcp_servers", []) or [] if tomllib else []
    except tomllib.TOMLDecodeError:
        existing = []
    merged = [s for s in existing if s.get("name") not in OUR_NAMES] + list(servers)
    rendered = _render_mcp(merged)

    # Drop any [[mcp_servers]] array-of-table blocks (we normalise to inline).
    text = re.sub(r"(?ms)^\[\[mcp_servers\]\].*?(?=^\[|\Z)", "", text)
    span = _inline_array_span(text, "mcp_servers")
    if span:
        return text[:span[0]] + rendered + text[span[1]:]
    # No existing definition: insert before the first table section (top-level
    # keys must precede tables), else at end.
    m = re.search(r"(?m)^\[", text)
    if m:
        return text[:m.start()] + rendered + "\n\n" + text[m.start():]
    return text.rstrip() + "\n" + rendered + "\n"


def _strip_marker_block(text: str, mark: str) -> str:
    start, end = f"# >>> {mark} >>>", f"# <<< {mark} <<<"
    out, skip = [], False
    for ln in text.splitlines(keepends=True):
        if ln.strip() == start:
            skip = True
            continue
        if ln.strip() == end:
            skip = False
            continue
        if not skip:
            out.append(ln)
    return "".join(out)


def _set_marker_block(text: str, mark: str, body: str) -> str:
    text = _strip_marker_block(text, mark)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + f"\n# >>> {mark} >>>\n{body.rstrip()}\n# <<< {mark} <<<\n"


def _backup(p: Path) -> None:
    bak = p.with_suffix(p.suffix + ".orchestra-bak")
    if p.exists() and not bak.exists():
        shutil.copy2(p, bak)


def install(vibe_home: Path, repo_dir: Path, ios_kit: Path | None,
            with_capabilities: bool = False) -> None:
    vibe_home.mkdir(parents=True, exist_ok=True)
    (vibe_home / "agents").mkdir(exist_ok=True)
    (vibe_home / "skills" / "ios").mkdir(parents=True, exist_ok=True)
    data = vibe_home / "orchestra" / "specialists" / "ios"
    data.mkdir(parents=True, exist_ok=True)

    # 1. Global orchestration posture.
    agents_md = vibe_home / "AGENTS.md"
    _backup(agents_md)
    posture = (repo_dir / "ORCHESTRA.md").read_text(encoding="utf-8")
    base = agents_md.read_text(encoding="utf-8") if agents_md.exists() else ""
    agents_md.write_text(_set_marker_block(base, POSTURE_MARK, posture), encoding="utf-8")

    # 2. Global MCP tools (+ keyless capabilities), merged into existing servers.
    servers = list(OUR_SERVERS) + (list(CAPABILITY_SERVERS) if with_capabilities else [])
    config = vibe_home / "config.toml"
    _backup(config)
    text = config.read_text(encoding="utf-8") if config.exists() else ""
    config.write_text(patch_mcp_servers(text, servers), encoding="utf-8")
    if with_capabilities:
        print("  connected keyless plugins: " + ", ".join(s["name"] for s in CAPABILITY_SERVERS))

    # 3a. /goal autonomous-loop skill (native /goal slash-command) + its safe,
    #     read-only verifier subagent (pins no model -> boots safely).
    (vibe_home / "skills" / "goal").mkdir(parents=True, exist_ok=True)
    goal_skill = Path(__file__).parent / "skills" / "goal" / "SKILL.md"
    (vibe_home / "skills" / "goal" / "SKILL.md").write_text(
        goal_skill.read_text(encoding="utf-8"), encoding="utf-8")
    (vibe_home / "agents" / "goal-verifier.toml").write_text(_GOAL_VERIFIER, encoding="utf-8")

    # 3b. iOS specialist: posture + patterns + a real vibe skill.
    (vibe_home / "skills" / "ios" / "SKILL.md").write_text(_IOS_SKILL, encoding="utf-8")
    if ios_kit and (ios_kit / "AGENTS.md").exists():
        shutil.copy2(ios_kit / "AGENTS.md", data / "AGENTS.md")
        if (ios_kit / "PATTERNS.md").exists():
            shutil.copy2(ios_kit / "PATTERNS.md", data / "PATTERNS.md")
        link = vibe_home / "agents" / "ios.toml"
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(ios_kit / "agents" / "ios.toml")
        print(f"  iOS specialist wired from {ios_kit}")
    else:
        print(f"  NOTE: vibe-ios-kit not found at {ios_kit}; set IOS_KIT and re-run.")

    # 4. Catalogue the key-requiring plugins for the user (never installed by us).
    from .catalog import CATALOG
    keyed = [c for c in CATALOG if c.needs_key]
    if keyed:
        print("  plugins you can add yourself (need a key):")
        for c in keyed:
            print(f"    {c.id}: {c.command}   [set {c.needs_key}]")


def uninstall(vibe_home: Path) -> None:
    agents_md = vibe_home / "AGENTS.md"
    if agents_md.exists():
        agents_md.write_text(_strip_marker_block(agents_md.read_text(encoding="utf-8"),
                                                 POSTURE_MARK), encoding="utf-8")
    config = vibe_home / "config.toml"
    if config.exists():
        config.write_text(patch_mcp_servers(config.read_text(encoding="utf-8"), []),
                          encoding="utf-8")
    shutil.rmtree(vibe_home / "orchestra", ignore_errors=True)
    shutil.rmtree(vibe_home / "skills" / "ios", ignore_errors=True)
    shutil.rmtree(vibe_home / "skills" / "goal", ignore_errors=True)
    link = vibe_home / "agents" / "ios.toml"
    if link.is_symlink():
        link.unlink()
    gv = vibe_home / "agents" / "goal-verifier.toml"
    if gv.exists():
        gv.unlink()
    print("Removed vibe-orchestra. (Backups *.orchestra-bak left in place.)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vibe-orchestra-install")
    ap.add_argument("--vibe-home", default=str(Path.home() / ".vibe"))
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--ios-kit", default="")
    ap.add_argument("--with-capabilities", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    args = ap.parse_args(argv)
    home = Path(args.vibe_home)
    if args.uninstall:
        uninstall(home)
    else:
        install(home, Path(args.repo), Path(args.ios_kit) if args.ios_kit else None,
                with_capabilities=args.with_capabilities)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
