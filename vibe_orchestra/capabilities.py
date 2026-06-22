"""Discover which catalog capabilities are actually wired into vibe right now."""
from __future__ import annotations

from pathlib import Path

from .catalog import CATALOG, Capability

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


def _installed_servers(vibe_home: Path) -> list[tuple[str, str]]:
    """(name, command) for every mcp_server declared in vibe's config."""
    config = vibe_home / "config.toml"
    if not config.exists() or tomllib is None:
        return []
    try:
        data = tomllib.loads(config.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return []
    out = []
    for s in data.get("mcp_servers", []) or []:
        cmd = s.get("command", "")
        if isinstance(cmd, list):
            cmd = " ".join(cmd)
        args = s.get("args", [])
        if isinstance(args, list):
            cmd = (cmd + " " + " ".join(map(str, args))).strip()
        out.append((str(s.get("name", "")), cmd))
    return out


def _skill_ids(vibe_home: Path) -> set[str]:
    ids = set()
    for base in (vibe_home / "skills", Path.home() / ".agents" / "skills"):
        if base.is_dir():
            for d in base.iterdir():
                if (d / "SKILL.md").exists():
                    ids.add(d.name)
    # The iOS specialist counts as installed once its posture is copied.
    if (vibe_home / "orchestra" / "specialists" / "ios" / "AGENTS.md").exists():
        ids.add("ios")
    return ids


def _pkg_token(command: str) -> str:
    """The distinguishing package token of a catalog command (e.g. the npm pkg)."""
    for part in command.split():
        if part.startswith("@") or "/" in part or part.endswith("-mcp"):
            return part
    return command.split()[-1] if command.split() else command


def installed_ids(vibe_home=None) -> set[str]:
    """Set of catalog ids that are live in vibe (MCP servers + skills)."""
    vibe_home = Path(vibe_home) if vibe_home else (Path.home() / ".vibe")
    servers = _installed_servers(vibe_home)
    server_names = {n for n, _ in servers}
    server_cmds = " || ".join(c for _, c in servers)
    skills = _skill_ids(vibe_home)
    found = set()
    for cap in CATALOG:
        if cap.kind == "skill":
            if cap.id in skills:
                found.add(cap.id)
            continue
        if cap.id in server_names or _pkg_token(cap.command) in server_cmds:
            found.add(cap.id)
    return found


def split_capabilities(caps: list[Capability], installed: set[str]):
    """Partition into (use = already installed, add = recommended to install)."""
    use = [c for c in caps if c.id in installed]
    add = [c for c in caps if c.id not in installed]
    return use, add
