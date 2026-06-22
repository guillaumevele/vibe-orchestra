"""MCP stdio server exposing the router as one tool the orchestrator calls.

    pip install "vibe-orchestra[mcp]"
    vibe-orchestra-mcp

The base package is dependency-free; `mcp` is pulled in only by the `[mcp]`
extra and imported here.
"""
from __future__ import annotations

from .catalog import CATALOG
from .capabilities import installed_ids
from . import models
from .router import ROUTES, RouterError, recommend


def _build_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            'vibe-orchestra-mcp needs the MCP SDK. Install:\n'
            '    pip install "vibe-orchestra[mcp]"'
        ) from exc

    server = FastMCP("vibe-orchestra")

    @server.tool()
    def route(task: str) -> str:
        """Classify a task and return the best Mistral model, specialist, tool,
        AND the real capabilities (MCP plugins / skills) to connect for its
        subject. Call this FIRST for any non-trivial task. It tells you: which
        model fits, whether to adopt a specialist (e.g. the iOS posture), which
        tool to reach for (e.g. vibe-fim_surgical_patch), which already-wired
        plugins to USE, and which to CONSIDER adding (with the command)."""
        try:
            rec = recommend(task)
        except RouterError as exc:
            return f"ERROR: {exc}"
        d, use, add = rec["decision"], rec["use"], rec["add"]
        lines = [f"route: {d.route}", f"model: {d.model}"]
        if d.specialist:
            lines.append(f"specialist: {d.specialist}")
        if d.tool:
            lines.append(f"tool: {d.tool}")
        if d.subjects:
            lines.append(f"subjects: {', '.join(d.subjects)}")
        if use:
            lines.append("use (already wired): " + ", ".join(c.id for c in use))
        for c in add:
            key = f" [set {c.needs_key}]" if c.needs_key else ""
            lines.append(f"consider adding: {c.id} — {c.command}{key}")
        lines.append(f"why: {d.reason}")
        return "\n".join(lines)

    @server.tool()
    def capabilities() -> str:
        """List the real plugins/skills the orchestrator knows, marking which are
        already wired into vibe and which can be added (with command + any key)."""
        live = installed_ids()
        out = []
        for c in CATALOG:
            mark = "wired" if c.id in live else "available"
            key = f" [needs {c.needs_key}]" if c.needs_key else ""
            out.append(f"[{mark}] {c.id} ({', '.join(c.subjects) or '-'}): {c.command}{key}")
        return "\n".join(out)

    @server.tool()
    def reason(question: str, context: str = "") -> str:
        """Hand a hard sub-problem to Magistral (chain-of-thought reasoning) and
        get the answer back — use for root-cause debugging, architecture, or
        math/logic, even while your own session runs a different model. This is
        real per-subtask model use, not a hint."""
        try:
            return models.reason(question, context)
        except models.ModelError as exc:
            return f"ERROR: {exc}"

    @server.tool()
    def vision(image: str, question: str) -> str:
        """Analyse an image / screenshot / UI with Pixtral. `image` is a local
        file path or an http(s) URL."""
        try:
            return models.vision(image, question)
        except models.ModelError as exc:
            return f"ERROR: {exc}"

    @server.tool()
    def quick(task: str) -> str:
        """Run a cheap, low-latency transform (extract / classify / reformat) on
        Ministral."""
        try:
            return models.quick(task)
        except models.ModelError as exc:
            return f"ERROR: {exc}"

    @server.tool()
    def routes() -> str:
        """List the full model policy: every route, its Mistral model, and when it
        applies."""
        return "\n".join(
            f"{r.name}: {r.model} — {r.when}" for r in ROUTES.values())

    return server


def main() -> None:
    _build_server().run()


if __name__ == "__main__":
    main()
