"""Command-line interface for vibe-orchestra."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .capabilities import installed_ids
from .catalog import CATALOG
from .router import ROUTES, RouterError, recommend


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vibe-orchestra",
        description="Route a task to the right Mistral model + specialist.")
    parser.add_argument("--version", action="version", version=f"vibe-orchestra {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    r = sub.add_parser("route", help="classify a task; print route + capabilities")
    r.add_argument("task", help="the task to route")
    r.add_argument("--json", action="store_true", help="emit the decision as JSON")

    sub.add_parser("routes", help="print the model policy (all routes)")
    sub.add_parser("capabilities", help="show real plugins/skills, installed vs available")

    args = parser.parse_args(argv)

    if args.command == "capabilities":
        live = installed_ids()
        print("Capabilities (• = wired into vibe now):\n")
        for c in CATALOG:
            mark = "•" if c.id in live else " "
            key = f"  [needs {c.needs_key}]" if c.needs_key else ""
            print(f" {mark} {c.id:20} {c.kind:6} {', '.join(c.subjects) or '-':22} {c.command}{key}")
        return 0

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
        rec = recommend(args.task)
    except RouterError as exc:
        print(f"vibe-orchestra: {exc}", file=sys.stderr)
        return 1
    decision, use, add = rec["decision"], rec["use"], rec["add"]

    if args.json:
        json.dump({**decision.as_dict(),
                   "use": [c.id for c in use],
                   "add": [{"id": c.id, "command": c.command, "needs_key": c.needs_key}
                           for c in add]}, sys.stdout)
        sys.stdout.write("\n")
        return 0

    print(f"route      : {decision.route}")
    print(f"model      : {decision.model}")
    if decision.tool:
        print(f"tool       : {decision.tool}")
    if decision.specialist:
        print(f"specialist : {decision.specialist}")
    if decision.subjects:
        print(f"subjects   : {', '.join(decision.subjects)}")
    if use:
        print(f"use        : {', '.join(c.id for c in use)}  (already wired)")
    for c in add:
        key = f"  [set {c.needs_key}]" if c.needs_key else ""
        print(f"consider   : {c.id} — {c.command}{key}")
    print(f"why        : {decision.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
