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
- the `route` and `surgical_patch` tools → `~/.vibe/config.toml` (global MCP),
- the iOS specialist (posture + pattern library) from `vibe-ios-kit`.

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
vibe-orchestra route "why does the app freeze after 90s on the Vera tab?"
#   route      : reasoning
#   model      : magistral-medium-latest
#   why        : root-cause debugging
vibe-orchestra routes          # print the full model policy
```

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
