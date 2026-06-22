"""vibe-orchestra — a Mistral model-and-specialist router for vibe.

Describe a task; a cheap classifier picks the right Mistral model, specialist, and
tool. A hand-designed take on multi-model orchestration — so you launch vibe and
it routes, instead of choosing models by hand.
"""
from __future__ import annotations

from .catalog import CATALOG, Capability, capabilities_for, subjects_for
from .capabilities import installed_ids
from .router import (
    DEFAULT_ROUTE,
    ROUTES,
    Decision,
    Route,
    RouterError,
    classify,
    ministral_classify,
    recommend,
)

__version__ = "0.3.0"

__all__ = [
    "classify",
    "recommend",
    "ROUTES",
    "Route",
    "Decision",
    "RouterError",
    "ministral_classify",
    "DEFAULT_ROUTE",
    "CATALOG",
    "Capability",
    "capabilities_for",
    "subjects_for",
    "installed_ids",
    "__version__",
]
