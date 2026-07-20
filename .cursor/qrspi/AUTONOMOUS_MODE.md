# QRSPI Autonomous Mode (Shadow AI Override)

This repository runs QRSPI **without human intervention gates**.

The original QRSPI stage docs contain "wait for the user" / "present and wait for approval" steps.
**Those waits are DISABLED here.** Replace them with the rules below.

## Global rule

When a stage says "ask the user" or "wait for approval":

1. Formulate the decision as if you were briefing a senior engineer.
2. Choose the **best option grounded in research / The Ledger / existing code**.
3. Record the choice and rationale in the stage artifact (`design.md`, `plan.md`, etc.).
4. **Proceed immediately** to the next required action in that stage.

Do **not** block the pipeline on human replies. The Engineering Manager reviews via PRs and Human-in-the-Loop checkpoints (separate from QRSPI gates).

## Per-stage overrides

### 1 — Question
- Finalize 3–7 neutral questions without waiting for edits.
- Still write `task.md` + `questions.md`.
- If the task is too trivial for QRSPI, note that in `task.md` and stop after Question (or skip QRSPI only if The Ledger explicitly allows a fast-path — default is: **use QRSPI**).

### 2 — Research
- Do not wait for follow-up questions.
- Produce the best `research.md` possible from codebase facts.
- Still spawn locator / analyzer / pattern-finder subagents in parallel.

### 3 — Design
- Still list 3–5 design questions with options + trade-offs.
- **Answer them yourself** in the same pass using research + The Ledger.
- Write `design.md` including a `## Autonomous Decisions` section that states each Q → chosen option → why.
- Do not wait for human design approval.

### 4 — Structure
- Produce vertical slices and finalize `structure.md` without waiting for reorder feedback.
- Prefer smaller, independently verifiable slices.

### 5 — Plan
- Resolve open questions with best judgment; never leave unresolved questions in `plan.md`.
- Document assumptions under `## Autonomous Assumptions`.

### 6 — Worktree
- In cloud / Cursor agent environments: create / use a feature branch matching `cursor/<descriptive-name>-bf7f` (or the run's registered branch convention). Prefer git worktrees when available; otherwise implement on the isolated feature branch.
- Do not wait for "Proceed?" confirmation — create the isolation boundary and continue.
- Always ensure QRSPI artifacts are present on the branch that will implement.

### 7 — Implement
- Do not pause for manual verification.
- Convert manual checks into automated tests/commands when feasible.
- For remaining manual checks: perform best-effort verification (scripted curls, pytest, compile) and check them off with a note `autonomous: verified via <command>`.
- Still stop and re-plan (via QRSPI go-back) on fundamental plan failures — do not silently invent scope.

### 8 — PR
- Push and open/update the PR without waiting.
- In this environment prefer `ManagePullRequest` over `gh pr create` when that tool is available; otherwise use `gh`.
- PR body must reference The Ledger and the QRSPI artifact directory.

## What is NOT overridden

- Research remains facts-only (no solutions).
- Research still must **not** read `task.md`.
- Context isolation between stages still applies.
- Human-in-the-Loop **product** checkpoints (e.g. `app/proxy/interceptor.py`) remain human-owned — QRSPI autonomy does not mean agents may fill those `TODO: Human Hands-On Implementation` blocks.
- Agent hierarchy (Opus / Grok / Composer / Sol) still applies.
