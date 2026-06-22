"""Command-line interface for vibe-orchestra."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .router import ROUTES, RouterError, classify


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vibe-orchestra",
        description="Route a task to the right Mistral model + specialist.")
    parser.add_argument("--version", action="version", version=f"vibe-orchestra {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    r = sub.add_parser("route", help="classify a task and print the route")
    r.add_argument("task", help="the task to route")
    r.add_argument("--json", action="store_true", help="emit the decision as JSON")

    sub.add_parser("routes", help="print the model policy (all routes)")

    args = parser.parse_args(argv)

    if args.command == "routes":
        for route in ROUTES.values():
            extra = []
            if route.tool:
                extra.append(f"tool={route.tool}")
            if route.specialist:
                extra.append(f"specialist={route.specialist}")
            tail = ("  (" + ", ".join(extra) + ")") if extra else ""
            print(f"{route.name:14} -> {route.model:24} {route.when}{tail}")
        return 0

    try:
        decision = classify(args.task)
    except RouterError as exc:
        print(f"vibe-orchestra: {exc}", file=sys.stderr)
        return 1

    if args.json:
        json.dump(decision.as_dict(), sys.stdout)
        sys.stdout.write("\n")
        return 0

    print(f"route      : {decision.route}")
    print(f"model      : {decision.model}")
    if decision.tool:
        print(f"tool       : {decision.tool}")
    if decision.specialist:
        print(f"specialist : {decision.specialist}")
    print(f"why        : {decision.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
