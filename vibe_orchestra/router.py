"""Route a task to the right Mistral model + specialist.

The idea (a hand-designed take on Sakana Fugu's model-coordination): you should
not have to pick which Mistral model to call. You describe the task; a cheap
classifier (Ministral) reads it and returns the best route — the model to use,
the specialist agent to adopt, and the tool to reach for. The orchestrator then
dispatches.

This is policy + a small classifier, not learned coordination. The classifier
backend is injectable, so the routing logic is fully testable with no network.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable

CHAT_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
CLASSIFIER_MODEL = "ministral-3b-latest"  # cheap + fast: classification is a tiny job

# A classifier backend: (system, user) -> raw JSON string with a "route" field.
ChatFn = Callable[[str, str], str]


class RouterError(Exception):
    pass


@dataclass(frozen=True)
class Route:
    name: str
    model: str        # the Mistral model this route runs on
    when: str         # one line: when this route applies
    tool: str = ""    # the tool to reach for, if any
    specialist: str = ""  # the specialist agent to adopt, if any


# The model policy. Each route names the Mistral model that fits the work.
ROUTES: dict[str, Route] = {
    "surgical-edit": Route(
        "surgical-edit", "codestral-latest",
        "Change a bounded region of a file that already compiles.",
        tool="vibe-fim_surgical_patch"),
    "agentic-build": Route(
        "agentic-build", "devstral-latest",
        "Implement a feature or a multi-file change end to end."),
    "reasoning": Route(
        "reasoning", "magistral-medium-latest",
        "Debug a hard root cause, design architecture, or do math/logic."),
    "vision": Route(
        "vision", "pixtral-latest",
        "Analyse an image, screenshot, photo, or UI."),
    "ios": Route(
        "ios", "devstral-latest",
        "SwiftUI / Metal / iOS app work — adopt the iOS posture.",
        specialist="ios"),
    "quick": Route(
        "quick", "ministral-3b-latest",
        "Trivial classify / extract / rename / format."),
    "chat": Route(
        "chat", "mistral-medium-latest",
        "Conversational: explain, plan, or discuss in prose."),
}
DEFAULT_ROUTE = "chat"

# Tokens that mean "this is iOS work" — the iOS specialist should win over a
# generic build/edit route when these appear, since it carries the posture.
_IOS_TOKENS = (
    "swiftui", "swift ui", ".swift", "metal", "shader", "xcode", "ios ",
    "iphone", "ipad", "uikit", "swift 6", "swiftdata", "foundationmodels",
    "liquid glass", "glasseffect", "timelineview", "scenephase", "widgetkit",
    "activitykit", "live activity", "dynamic island",
)

_SYSTEM = (
    "You are a task router for Mistral models. Read the task and pick exactly one "
    "route. Routes:\n"
    + "\n".join(f"- {r.name}: {r.when}" for r in ROUTES.values())
    + "\nPrefer 'ios' for any SwiftUI / Metal / iOS work, even if it is also a "
    "build. Reply with JSON: {\"route\": <one of the names>, \"reason\": <short>}."
)


@dataclass(frozen=True)
class Decision:
    route: str
    model: str
    reason: str
    tool: str
    specialist: str
    subjects: tuple = ()

    def as_dict(self) -> dict:
        return {"route": self.route, "model": self.model, "tool": self.tool,
                "specialist": self.specialist, "subjects": list(self.subjects),
                "reason": self.reason}


def ministral_classify(system: str, user: str, *, api_key: str | None = None,
                       timeout_s: int = 30) -> str:
    """Default classifier backend: one cheap Ministral call, JSON mode."""
    api_key = api_key or os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        raise RouterError("MISTRAL_API_KEY is not set (and no api_key was provided).")
    body = json.dumps({
        "model": CLASSIFIER_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }).encode("utf-8")
    request = urllib.request.Request(
        CHAT_ENDPOINT, data=body, method="POST",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise RouterError(f"classifier HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise RouterError(f"classifier request failed: {exc}") from exc
    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RouterError(f"unexpected classifier response: {payload}") from exc


def _looks_ios(task: str) -> bool:
    low = task.lower()
    return any(tok in low for tok in _IOS_TOKENS)


def classify(task: str, *, chat_fn: ChatFn | None = None) -> Decision:
    """Classify a task into a Route decision. `chat_fn(system, user)` returns the
    classifier's raw JSON; injectable so this is testable with no network."""
    if not task or not task.strip():
        raise RouterError("empty task.")
    chat_fn = chat_fn or ministral_classify
    raw = chat_fn(_SYSTEM, task)
    try:
        name = str(json.loads(raw).get("route", "")).strip()
    except (ValueError, TypeError):
        name = ""
    route = ROUTES.get(name)
    reason = ""
    if route is None:
        route = ROUTES[DEFAULT_ROUTE]
        reason = f"unrecognised route {name!r}; fell back to {DEFAULT_ROUTE}."
    else:
        try:
            reason = str(json.loads(raw).get("reason", "")).strip()
        except (ValueError, TypeError):
            reason = ""
    # Specialist override: iOS work adopts the iOS posture even when the model
    # classified it as a generic build/edit.
    if route.name in ("agentic-build", "surgical-edit") and _looks_ios(task):
        ios = ROUTES["ios"]
        reason = (reason + " | iOS content -> iOS specialist.").strip(" |")
        route = ios
    from .catalog import subjects_for
    return Decision(route=route.name, model=route.model, reason=reason,
                    tool=route.tool, specialist=route.specialist,
                    subjects=subjects_for(task, route.name))


def recommend(task: str, *, chat_fn: ChatFn | None = None, vibe_home=None) -> dict:
    """Full picture: the route decision plus the REAL capabilities to connect for
    this task's subjects — split into `use` (already wired into vibe) and `add`
    (recommended, with the command and any key to set)."""
    from .capabilities import installed_ids, split_capabilities
    from .catalog import capabilities_for
    decision = classify(task, chat_fn=chat_fn)
    caps = capabilities_for(decision.subjects)
    use, add = split_capabilities(caps, installed_ids(vibe_home))
    return {"decision": decision, "use": use, "add": add}
