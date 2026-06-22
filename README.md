# vibe-orchestra

**A Mistral model-and-specialist router for [`vibe`](https://github.com/mistralai).**
Describe a task; it routes to the right Mistral model, specialist, and tool — so
you launch `vibe` and it orchestrates, instead of picking models by hand.

[![CI](https://github.com/guillaumevele/vibe-orchestra/actions/workflows/ci.yml/badge.svg)](https://github.com/guillaumevele/vibe-orchestra/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![deps](https://img.shields.io/badge/dependencies-none-brightgreen)

---

## The idea

Inspired by [Sakana AI's Fugu](https://sakana.ai/fugu/) — *you should not manage
which model to call*. Fugu coordinates a pool of models with **learned**
strategies (an evolved coordinator + an RL-trained conductor). `vibe-orchestra`
does not learn coordination; it is the practical, **hand-designed** slice you can
run today: a cheap classifier picks the route, and a model policy maps each route
to the Mistral model, specialist, and tool that fit.

```
task ──▶ route()  (Ministral, cheap)
            │
   surgical-edit ─▶ Codestral FIM     · tool: vibe-fim surgical_patch
   ios          ─▶ Devstral           · specialist: iOS posture + patterns
   reasoning    ─▶ Magistral
   vision       ─▶ Pixtral
   agentic-build─▶ Devstral
   quick        ─▶ Ministral
   chat         ─▶ Mistral medium
```

## Install — then `vibe`, and basta

```bash
git clone https://github.com/guillaumevele/vibe-orchestra && cd vibe-orchestra
IOS_KIT=/path/to/vibe-ios-kit ./install.sh
```

`install.sh` wires everything **globally and reversibly** (it backs up the files
it touches and edits only inside marked blocks):

- the orchestration posture → `~/.vibe/AGENTS.md` (loaded by *every* session),
- the `route` + `surgical_patch` tools → `~/.vibe/config.toml` (global MCP),
- the iOS specialist (posture + 38 patterns + a real `ios` vibe skill) from `vibe-ios-kit`.

Add `--with-capabilities` to also connect a curated set of real, **keyless** MCP
plugins so the orchestrator is autonomous out of the box:

```bash
./install.sh --with-capabilities     # + apple-docs, context7, sequential-thinking
```

It pre-warms the npm cache and gives those servers a generous startup timeout —
a cold `npx` download otherwise exceeds vibe's 10s limit and destabilises MCP
init (learned the hard way). Plugins that need a key (github, supabase, brave)
are **catalogued with their command and env var for you to add yourself** — this
project never ships or asks for secrets.

After that, anywhere — no `--agent`, no per-project copy:

```bash
vibe "round the body of computeScore() to 2 decimals, leave the rest"
vibe "add a shimmer Metal loader to onboarding, gated on scenePhase"
```

Plain `vibe` calls `route()` to pick the model/specialist, then edits via
`surgical_patch` (Codestral FIM, bounded). Undo with `./install.sh --uninstall`.

## Use the router directly

```bash
pip install vibe-orchestra
vibe-orchestra route "verify the SwiftUI glassEffect API then add a glass tab bar"
#   route      : ios
#   model      : devstral-latest
#   subjects   : apple-docs, ios
#   use        : ios, apple-docs        (already wired)
#   why        : SwiftUI work -> iOS specialist
vibe-orchestra routes          # the model policy
vibe-orchestra capabilities    # real plugins/skills: wired vs available
```

## Connect real plugins per subject

`route` is **capability-aware**: it returns not just a model and specialist but
the real plugins/skills that serve the task's subject — split into ones already
**wired** into vibe and ones to **consider adding** (with the exact command and
any key). The catalog is verified, public packages only:

| subject | plugin | key |
|---|---|---|
| iOS / Apple APIs | `apple-docs` | — |
| library docs | `context7` | — |
| hard reasoning | `sequential-thinking` | — |
| browser / scrape | `playwright` | — |
| backend / Postgres | `supabase` | `SUPABASE_ACCESS_TOKEN` |
| repos / PRs | `github` | `GITHUB_PERSONAL_ACCESS_TOKEN` |
| web search | `brave-search` | `BRAVE_API_KEY` |

That is the autonomy: the orchestrator reaches for the right real tool per
subject instead of guessing.

```python
from vibe_orchestra import classify
d = classify("add a SwiftUI settings screen")
d.route, d.model, d.specialist     # ('ios', 'devstral-latest', 'ios')
```

The classifier backend is injectable, so the routing logic is fully testable with
no network:

```python
classify("rename foo to bar", chat_fn=lambda system, user: '{"route": "surgical-edit"}')
```

## Honest limits

- **Coordination is hand-designed, not learned.** Fugu's edge is the trained
  coordinator; this is a policy + a classifier. It is transparent and cheap, not
  evolved.
- **Within one session the driving model is fixed.** `route()` tells you the
  ideal model and gives you the tools/specialists to act on it — real today for
  **edits** (Codestral FIM) and **iOS** (the specialist posture). Routes whose
  ideal model differs and have no backing tool yet are surfaced, not silently
  switched. Full per-subtask model switching grows by adding more model-backed
  tools — that is the roadmap, stated plainly so nothing is overclaimed.

## Specialties

The iOS specialist is [`vibe-ios-kit`](https://github.com/guillaumevele/vibe-ios-kit)
(build posture + 38 distilled iOS 26/27 patterns + a runnable lint). The registry
is extensible: a specialist is a `vibe` agent plus a posture the orchestrator
adopts when `route` selects it.

## License

MIT © Guillaume Vele
