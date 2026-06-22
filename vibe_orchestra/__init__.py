"""vibe-orchestra — a Mistral model-and-specialist router for vibe.

Describe a task; a cheap classifier picks the right Mistral model, specialist, and
tool. A hand-designed take on multi-model orchestration — so you launch vibe and
it routes, instead of choosing models by hand.
"""
from __future__ import annotations

from .router import (
    DEFAULT_ROUTE,
    ROUTES,
    Decision,
    Route,
    RouterError,
    classify,
    ministral_classify,
)

__version__ = "0.1.0"

__all__ = [
    "classify",
    "ROUTES",
    "Route",
    "Decision",
    "RouterError",
    "ministral_classify",
    "DEFAULT_ROUTE",
    "__version__",
]
