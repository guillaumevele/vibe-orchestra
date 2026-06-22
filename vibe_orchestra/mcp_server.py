"""MCP stdio server exposing the router as one tool the orchestrator calls.

    pip install "vibe-orchestra[mcp]"
    vibe-orchestra-mcp

The base package is dependency-free; `mcp` is pulled in only by the `[mcp]`
extra and imported here.
"""
from __future__ import annotations

from .router import ROUTES, RouterError, classify


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
        """Classify a task and return the recommended Mistral model, specialist,
        and tool. Call this FIRST when a task could use a different model than the
        current one. Returns one line you act on: which model fits, whether to
        adopt a specialist (e.g. the iOS posture), and which tool to reach for
        (e.g. vibe-fim_surgical_patch for a bounded edit)."""
        try:
            d = classify(task)
        except RouterError as exc:
            return f"ERROR: {exc}"
        lines = [f"route: {d.route}", f"model: {d.model}"]
        if d.specialist:
            lines.append(f"specialist: {d.specialist}")
        if d.tool:
            lines.append(f"tool: {d.tool}")
        lines.append(f"why: {d.reason}")
        return "\n".join(lines)

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
