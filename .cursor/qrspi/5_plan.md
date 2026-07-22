---
description: Tactical implementation plan — the agent's working document
model: opus
argument-hint: "thoughts/qrspi/<id>/"
---

> **AUTONOMOUS AGENT OVERRIDE (this repo):** Do **not** wait for human approval.
> Follow [AUTONOMOUS_MODE.md](AUTONOMOUS_MODE.md). Enforce [CONTEXT_ISOLATION.md](CONTEXT_ISOLATION.md):
> run this stage in a **fresh subagent** with **only** the allowed artifact inputs listed in [README.md](README.md).
> The Ledger (`architecture_and_roadmap.md`) is law. Never fill `TODO: Human Hands-On Implementation` blocks.

# Plan — Tactical Implementation Details

Expand the structure outline into a detailed, actionable implementation plan. This is the **agent's working document** — it should contain everything needed to implement without further context. The human reviews the design and structure; this document is for spot-checking.

## Input

Read `$ARGUMENTS/structure.md`, `$ARGUMENTS/design.md`, and `$ARGUMENTS/research.md`.

## Process

1. **Read all three artifacts fully.**

2. **For each phase in `structure.md`**, expand into full implementation detail:
   - Exact file paths and what changes in each
   - Code snippets for non-trivial changes (new functions, type definitions, migrations)
   - Specific automated verification commands
   - Manual verification steps

3. **Write `plan.md`** to the artifact directory:

   ```markdown
   # Implementation Plan

   ## Overview
   [1-2 sentences from the design's desired end state]

   ## Phase 1: [Name from structure.md]

   ### Changes

   #### 1. [File or component group]
   **File**: `path/to/file.ext`
   **Action**: [create / modify / delete]

   ```language
   // Key code to add or modify
   ```

   #### 2. [Next file]
   ...

   ### Verification
   #### Automated
   - [ ] [project test/lint command] passes
   - [ ] [specific command for this phase]

   #### Manual
   - [ ] [what to check and expected behavior]

   ---

   ## Phase 2: [Name]
   ...
   ```

4. **Ensure completeness**:
   - Every file mentioned in `structure.md` must appear in the plan
   - No unresolved questions — if you find one, **decide autonomously**, document under `## Autonomous Assumptions`, and continue
   - Verification steps must be concrete commands, not vague descriptions

5. **AUTONOMOUS:** Finalize `plan.md`. Note deviations from `structure.md` and why inside the plan.

## Output

- File written: `thoughts/qrspi/<id>/plan.md`
- Tell the user: "Next: run `/qrspi/6_worktree thoughts/qrspi/<id>/` to set up an isolated worktree, or `/qrspi/7_implement thoughts/qrspi/<id>/` to implement in the current tree."

## Rules

- The plan must be self-contained. An agent reading only `plan.md` should be able to implement the feature.
- Follow the phase order from `structure.md`. Do not reorganize.
- Include code snippets for anything non-obvious. Skip boilerplate.
- Checkboxes (`- [ ]`) are mandatory for all verification steps — they track progress during implementation.
- No open questions in the final plan. Resolve autonomously and document under `## Autonomous Assumptions`.
- Use the project's existing test/lint/build commands for verification. Check CLAUDE.md, Makefile, or package.json for the right commands.
- Aim for a plan that's proportional to the work — roughly 1 line of plan per 1-2 lines of code expected.
- Only include changes described in `design.md` and `structure.md`. Do not add refactoring, cleanup, or improvements to adjacent code — even if it's obviously messy.
- If the plan includes schema migrations, include updating any test assertions that reference the current schema version.
- If the plan includes codegen steps, note what to do if codegen fails or is unavailable (e.g., manually adding fields to generated files as a fallback).

## Secure generation constraints

Mandatory for any plan that touches parsing, auth, networking, `/v1` routes, or secrets:

- **Defensive prompts:** Name concrete libraries and attack classes (e.g. `defusedxml` / XXE, max payload size, SSRF egress allowlists). Do not hand-wave “sanitize input.”
- **Reuse repo patterns:** Prefer existing `app/security/` helpers and provider adapters. Do not invent parallel utilities.
- **Tests in the same change:** Include test steps for malformed, null, oversized, and authz-denied cases in the same phase as the feature.
- **No silent defaults:** Forbid “TODO add auth later,” bare `except Exception: pass`, and new dependencies without lockfile update + justification.
- **New `/v1` routes:** Authz, rate-limiting, and audit logging must appear as explicit plan steps (or an explicit deferral with rationale — never silent).
- **Secrets & trust:** Never hardcode secrets. Never trust client-side checks as authorization.

## When to Go Back

If expanding the structure reveals that a phase can't be implemented as outlined — missing information, incorrect assumptions, or a structural issue — tell the user and suggest re-running `/qrspi/4_structure` or `/qrspi/3_design` rather than writing a plan you know is flawed.
