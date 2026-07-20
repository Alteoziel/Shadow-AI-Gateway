# QRSPI Workflow (Mandatory)

**Q**uestion → **R**esearch → **S**tructure path via Design → **P**lan → **I**mplement (+ Worktree + PR)

This directory is the canonical QRSPI playbook for Shadow AI Guardrail Gateway.
It is **law** via [`architecture_and_roadmap.md`](../../architecture_and_roadmap.md) (The Ledger).

## Stages (run in order)

| # | File | Purpose | Allowed artifact inputs (only) |
|---|------|---------|--------------------------------|
| 1 | [`1_question.md`](1_question.md) | Neutral research questions | Task description / ticket (writes `task.md` + `questions.md`) |
| 2 | [`2_research.md`](2_research.md) | Facts-only research | **`questions.md` only** — never `task.md` |
| 3 | [`3_design.md`](3_design.md) | Design decisions | `task.md`, `questions.md`, `research.md` |
| 4 | [`4_structure.md`](4_structure.md) | Vertical slices | `design.md`, `research.md` |
| 5 | [`5_plan.md`](5_plan.md) | Tactical plan | `structure.md`, `design.md`, `research.md` |
| 6 | [`6_worktree.md`](6_worktree.md) | Isolated branch / worktree | Artifact dir + `plan.md` |
| 7 | [`7_implement.md`](7_implement.md) | Execute plan | **`plan.md` primary** |
| 8 | [`8_pr.md`](8_pr.md) | Open / update PR | `design.md` (+ diff / commits) |

## Subagents

Prompt templates live in [`agents/`](agents/):

- `codebase-locator` — WHERE files live
- `codebase-analyzer` — HOW code works (`file:line`)
- `codebase-pattern-finder` — existing patterns / examples
- `web-search-researcher` — external / current docs

## Autonomous mode (this repo)

See [`AUTONOMOUS_MODE.md`](AUTONOMOUS_MODE.md). **No human approval gates.**
The orchestrating agent answers every stage question with its best grounded judgment and proceeds.

## Context isolation (non-negotiable)

See [`CONTEXT_ISOLATION.md`](CONTEXT_ISOLATION.md). Each QRSPI stage runs in a **fresh subagent** with only the files listed above. Do not share chat history across stages.

## Artifacts

All run artifacts go under:

```text
thoughts/qrspi/<YYYY-MM-DD-brief-description>/
  task.md
  questions.md
  research.md
  design.md
  structure.md
  plan.md
```
