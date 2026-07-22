---
description: Design discussion — align on where we are going before planning how
model: opus
argument-hint: "thoughts/qrspi/<id>/"
---

> **AUTONOMOUS AGENT OVERRIDE (this repo):** Do **not** wait for human approval.
> Follow [AUTONOMOUS_MODE.md](AUTONOMOUS_MODE.md). Enforce [CONTEXT_ISOLATION.md](CONTEXT_ISOLATION.md):
> run this stage in a **fresh subagent** with **only** the allowed artifact inputs listed in [README.md](README.md).
> The Ledger (`architecture_and_roadmap.md`) is law. Never fill `TODO: Human Hands-On Implementation` blocks.

# Design — Where Are We Going?

Create a ~200-line design document that captures the current state, desired end state, design decisions, and patterns to follow. This is the **lowest-cost point for direction changes** — get alignment here before investing in detailed planning.

## Input

Read `$ARGUMENTS/task.md`, `$ARGUMENTS/questions.md`, and `$ARGUMENTS/research.md`.

## Process

1. **Read all three artifacts fully.** `task.md` tells you what we're building. `research.md` tells you what exists. Understand both before proceeding.

2. **Targeted exploration**: If the research revealed areas that need deeper investigation for design decisions, spawn **codebase-pattern-finder** or **codebase-analyzer** agents to examine specific patterns or approaches.

3. **AUTONOMOUS design decisions (replaces human Q&A).** Before writing `design.md`, you MUST:
   - List 3-5 design questions that would normally require human judgment
   - Present options with trade-offs for each, grounded in research
   - **Answer each question yourself** with the best option (Ledger + research + patterns)
   - Record Q → chosen option → rationale under `## Autonomous Decisions` in `design.md`

   Do NOT skip the questions. Do NOT wait for a human. Do NOT write a design without explicitly choosing.

4. **Write `design.md`** (~200 lines) to the artifact directory:

   ```markdown
   # Design Discussion

   ## Current State
   [What exists today, grounded in research findings with file:line refs]

   ## Desired End State
   [What we're building and how to verify it's correct]

   ## Patterns to Follow
   [Existing codebase patterns the implementation should match, with file:line refs.
   Flag any patterns the research found that should NOT be followed.]

   ## Design Decisions
   1. **[Decision name]**: [chosen option] — [why]
   2. **[Decision name]**: [chosen option] — [why]
   ...

   ## What We're NOT Doing
   [Explicit scope boundaries to prevent creep]

   ## Open Risks
   [Anything uncertain that might surface during implementation]
   ```

5. **AUTONOMOUS:** Finalize `design.md` and proceed. Human review happens via PR, not a QRSPI gate.

## Output

- File written: `thoughts/qrspi/<id>/design.md`
- Tell the user: "Next: run `/qrspi/4_structure thoughts/qrspi/<id>/`"

## Rules

- ~200 lines max. This is a steering document, not a specification.
- Every pattern reference must cite `file:line` from the research.
- You MUST enumerate design questions and answer them autonomously before writing. No exceptions.
- "Patterns to Follow" is critical — call out both good and bad patterns found in the codebase.
- "What We're NOT Doing" prevents scope creep downstream.

## Secure generation constraints

Mandatory for any design that touches parsing, auth, networking, `/v1` routes, or secrets:

- **Defensive prompts:** Name concrete libraries and attack classes (e.g. `defusedxml` / XXE, max payload size, SSRF egress allowlists). Do not hand-wave “sanitize input.”
- **Reuse repo patterns:** Prefer existing `app/security/` helpers and provider adapters. Do not invent parallel utilities.
- **Tests in the same change:** Plan for malformed, null, oversized, and authz-denied cases alongside the happy path.
- **No silent defaults:** Forbid “TODO add auth later,” bare `except Exception: pass`, and new dependencies without lockfile update + justification.
- **New `/v1` routes:** Authz, rate-limiting, and audit logging must be considered explicitly in the design.
- **Secrets & trust:** Never hardcode secrets. Never trust client-side checks as authorization.

## When to Go Back

If the research is missing critical information needed for design decisions — the questions missed an important area of the codebase — tell the user and suggest re-running `/qrspi/1_question` and `/qrspi/2_research` to fill the gap before proceeding with an incomplete design.
