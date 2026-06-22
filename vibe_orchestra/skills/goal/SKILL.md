---
name: goal
description: Turn a one-line GOAL into an autonomous, verified run. Decompose into
  subtasks, route each to the best Mistral model/specialist/plugin, dispatch to the
  smallest mechanism that works, and refuse to mark a step done until a tool-call
  proves it. A hand-designed Thinker/Worker/Verifier loop for vibe.
---

# /goal — autonomous orchestration loop

You are the orchestrator. Run this loop for the user's GOAL. Keep the plan and the
report on disk so they survive compaction. Route first; prove every step.

## Prerequisite

The dispatch tools `reason`/`vision`/`quick` make direct Mistral API calls and need
`MISTRAL_API_KEY` in this session's environment. If it is unset, say so and fall
back to the driving model + wired plugins for those steps.

## The loop

1. **Decompose (Thinker).** Break the GOAL into 2–6 ordered subtasks. For each,
   write an **explicit acceptance check now** — the exact bash command / test /
   build / diff / screenshot-read / re-derivation that will later prove it. Write
   this to `./.vibe-goal/PLAN.md`. For a genuinely hard decomposition only, you may
   call `reason` (Magistral). Do not over-split: a trivial GOAL skips fan-out.

2. **Route (per non-trivial subtask).** Call the `route` tool. It returns the
   model, specialist, tool, subjects, and the real plugins to `use` (already wired)
   or `consider` (add, with command + key). This is your coordination layer.

3. **Dispatch — smallest mechanism that works**, in this priority order:
   - **surgical-edit** → `vibe-fim_surgical_patch` (bounded Codestral FIM; it
     rejects a result that no longer parses). Never rewrite a working file for a
     few lines.
   - **vision** → `vision` (Pixtral) on a screenshot/image.
   - **reasoning** → `reason` (Magistral) for a hard sub-answer.
   - **quick** → `quick` (Ministral) for extract/classify/reformat.
   - **ios** → load the `ios` skill and follow its posture; edit Swift via
     `surgical_patch`.
   - **agentic-build / chat** → do it inline on the driving model, using the
     plugins `route` told you to `use` (apple-docs, context7, …).
   - Delegate to a subagent via the `task` tool when a subtask needs a different
     model pinned across many turns, or strong context isolation. The provided
     subagents: **`goal-thinker`** (pins Magistral for deep multi-turn reasoning —
     hard root-cause, architecture, proofs) and **`goal-verifier`** (read-only,
     re-runs a proof). For a one-shot model answer the tools above are cheaper.

4. **Verify (Verifier).** After each subtask, run its acceptance check. **The verify
   step MUST be a tool call** (bash / vision / a re-read of the diff), never prose.
   Paste the literal evidence into `./.vibe-goal/REPORT.md`: the pass line from
   stdout; the accepted patch + diff; the screenshot read back; the API fact checked
   against `apple-docs`/`context7` (not memory). Never accept a model's word as proof
   of a code change. For independent verification you may dispatch the
   `goal-verifier` subagent (read/grep/bash only — it cannot edit, so it cannot
   fix-then-claim). On failure: log it in PLAN.md and **re-route/re-plan** that step;
   retry budget **2**, then surface it as NOT-DONE.

5. **Synthesize.** When all checks pass, finalize `REPORT.md`: per subtask, the route
   chosen, the model/tool actually used, and the exact proof observed. Surface any
   step still owner-gated or NOT-DONE — never hide it. State which model each step
   ran on so nothing is overclaimed.

## Honest limits (state these; do not overclaim)

- This skill is **instructions**, not a runtime — the loop runs only as faithfully
  as you follow it. There is no engine forcing step N before N+1.
- Within one session the **driving model is fixed**. You reach other Mistral models
  only via the single-shot tools (`reason`/`vision`/`quick`/`surgical_patch`) or a
  subagent — never by silently swapping your own model.
- Fan-out is **sequential**, not parallel. "Thinker/Worker/Verifier" means role
  separation, not concurrent workers.
- A model-pinning subagent loads fine at discovery but **crashes on first dispatch**
  if its `active_model` alias is not in `config.models`. `goal-thinker` avoids this
  by co-declaring its own Magistral provider+model block (and `thinking="off"`,
  since magistral rejects a reasoning_effort request) — proven to boot by dispatch.
  `goal-verifier` pins nothing.
- Delegating to a subagent triggers a permission **ASK** the first time. An
  unattended run pauses there unless you have allowlisted `goal-*` yourself.
