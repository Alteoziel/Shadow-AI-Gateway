# QRSPI Context Isolation Law

**Why:** Cross-stage context bleed causes researchers to "solve" the feature, designers to invent facts, and implementers to ignore the plan. Isolation keeps each stage honest.

## Mandatory mechanics

1. **One orchestrator, many isolated stage runners.** The parent agent may sequence stages, but **each stage's heavy work runs in a fresh subagent** (Task tool / dedicated agent) with a **new context**.
2. **File-scoped inputs only.** The stage subagent prompt may include:
   - The stage playbook path under `.cursor/qrspi/`
   - `.cursor/qrspi/AUTONOMOUS_MODE.md`
   - `.cursor/qrspi/CONTEXT_ISOLATION.md`
   - `architecture_and_roadmap.md` (The Ledger) — always allowed as global law
   - **Only** the artifact files listed for that stage in [`README.md`](README.md)
3. **Forbidden inputs by stage:**
   - Research (`2_research`): must **not** receive `task.md`, tickets, design docs, or the original feature pitch
   - Implement (`7_implement`): primary input is `plan.md`; do not dump full prior chat
   - Question (`1_question`): may receive the task; must not pre-load a finished design
4. **No shared chat history across stages.** Do not `resume` a previous stage subagent for a later stage. Start fresh. Artifact files on disk are the only bridge.
5. **Subagent file allowlists.** When spawning locator/analyzer/pattern-finder agents, give them:
   - The specific questions (1–2 max)
   - Optional path hints from prior *same-stage* findings
   - Explicit instruction: "You may only search/read what you need for these questions. Do not propose solutions."
6. **Artifacts are the API.** If a later stage needs information, it must be written into `research.md` / `design.md` / `structure.md` / `plan.md`. If it's not in the artifact, it does not exist for that stage.
7. **Go-back is a new run.** Re-running an earlier stage means a new subagent + updated artifacts — not mutating prior chat.

## Orchestrator checklist (copy into every parent agent run)

```text
[ ] Read architecture_and_roadmap.md (The Ledger)
[ ] Read .cursor/qrspi/README.md + AUTONOMOUS_MODE.md + CONTEXT_ISOLATION.md
[ ] Create/reuse thoughts/qrspi/<id>/
[ ] For EACH stage 1→8:
    [ ] Spawn a FRESH subagent
    [ ] Pass ONLY allowed files for that stage
    [ ] Wait for artifact write
    [ ] Do NOT resume that subagent for the next stage
[ ] Never fill Human Hands-On checkpoint TODOs
```

## Anti-patterns (ban these)

- One mega-agent doing Question through Implement in a single context
- Pasting `task.md` into the Research agent "for clarity"
- Resuming the Design agent to Implement
- Letting Implement invent features not in `plan.md`
- Skipping QRSPI because "it's a small change" (unless The Ledger fast-path applies)
