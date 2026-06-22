"""A catalog of REAL capabilities (MCP servers + skills) the orchestrator can
connect, mapped to the subjects they serve.

Every entry is a verified, public package (npm/pip) or a local tool — nothing
invented. Entries that need a secret declare the env var; this project never
ships or asks for secrets, it only tells you the command and which key to set.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Capability:
    id: str
    kind: str               # "mcp" | "skill" | "tool"
    why: str
    command: str            # how to run/add it
    subjects: tuple = ()    # subject tags it serves
    needs_key: str = ""     # env var name, or "" if keyless
    builtin: bool = False   # installed by vibe-orchestra itself


# Verified packages (npm view confirmed) + local tools. Keep this honest.
CATALOG: list[Capability] = [
    Capability("vibe-fim", "mcp",
               "Bounded Swift/code edits via Codestral FIM (surgical_patch).",
               "vibe-fim-mcp", subjects=("edit",), builtin=True),
    Capability("vibe-orchestra", "mcp",
               "Route a task to the best model/specialist/tool.",
               "vibe-orchestra-mcp", subjects=("route",), builtin=True),
    Capability("ios", "skill",
               "iOS 26/27 build posture + 38 distilled patterns (vibe-ios-kit).",
               "installed by vibe-orchestra (iOS specialist)",
               subjects=("ios",), builtin=True),
    Capability("apple-docs", "mcp",
               "Live Apple framework docs, WWDC, symbol search — verify iOS APIs.",
               "npx -y @kimsungwhee/apple-docs-mcp",
               subjects=("ios", "apple-docs")),
    Capability("context7", "mcp",
               "Current docs for any library/framework/SDK by name.",
               "npx -y @upstash/context7-mcp", subjects=("docs",)),
    Capability("sequential-thinking", "mcp",
               "Structured multi-step reasoning scratchpad.",
               "npx -y @modelcontextprotocol/server-sequential-thinking",
               subjects=("reasoning",)),
    Capability("playwright", "mcp",
               "Drive a real browser: navigate, scrape, screenshot, test.",
               "npx -y @playwright/mcp", subjects=("web",)),
    Capability("github", "mcp",
               "Repos, PRs, issues, code search.",
               "npx -y @modelcontextprotocol/server-github",
               subjects=("vcs",), needs_key="GITHUB_PERSONAL_ACCESS_TOKEN"),
    Capability("supabase", "mcp",
               "Postgres/backend: tables, SQL, edge functions, logs.",
               "npx -y @supabase/mcp-server-supabase",
               subjects=("backend",), needs_key="SUPABASE_ACCESS_TOKEN"),
    Capability("brave-search", "mcp",
               "Web + local search.",
               "npx -y @modelcontextprotocol/server-brave-search",
               subjects=("research",), needs_key="BRAVE_API_KEY"),
    Capability("filesystem", "mcp",
               "Scoped file read/write outside the project root.",
               "npx -y @modelcontextprotocol/server-filesystem",
               subjects=("files",)),
    Capability("memory", "mcp",
               "Persistent knowledge graph across sessions.",
               "npx -y @modelcontextprotocol/server-memory",
               subjects=("memory",)),
]

CATALOG_BY_ID = {c.id: c for c in CATALOG}

# Route name -> subjects that route implies.
_ROUTE_SUBJECTS: dict[str, tuple] = {
    "ios": ("ios", "apple-docs"),
    "reasoning": ("reasoning",),
    "surgical-edit": ("edit",),
    "vision": (),
    "agentic-build": (),
    "quick": (),
    "chat": (),
}

# Keyword -> subject, for cross-cutting subjects the route name does not capture.
_KEYWORD_SUBJECTS: list[tuple[tuple, str]] = [
    (("supabase", "postgres", "database", "edge function", "sql ", " db "), "backend"),
    (("github", "pull request", " pr ", " pr.", "issue", "commit", "git "), "vcs"),
    (("browser", "scrape", "website", "web page", "playwright", "crawl"), "web"),
    (("docs", "documentation", "library", "api of", "how to use", "package"), "docs"),
    (("search", "research", "look up", "find out", "latest news"), "research"),
]


def subjects_for(task: str, route: str) -> tuple:
    """Subjects a task touches: from its route plus keyword detection."""
    subjects = set(_ROUTE_SUBJECTS.get(route, ()))
    low = f" {task.lower()} "
    for needles, subject in _KEYWORD_SUBJECTS:
        if any(n in low for n in needles):
            subjects.add(subject)
    return tuple(sorted(subjects))


def capabilities_for(subjects) -> list[Capability]:
    """Catalog entries serving any of these subjects, in catalog order."""
    want = set(subjects)
    return [c for c in CATALOG if want & set(c.subjects)]
