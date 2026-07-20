# Implementation Plan

## Overview

Land a documentation-only process-law update that makes QRSPI mandatory for developmental work, makes the Ledger's conflict precedence explicit, clarifies the Step 6 CI-vs-dashboard split, and preserves the human-owned `app/proxy/interceptor.py` checkpoint.

No product behavior changes are in scope.

---

## Phase 1: Ledger Law and Workflow Discovery

### Changes

#### 1. Ledger opening contract
**File**: `architecture_and_roadmap.md`  
**Action**: modify

At the top of the file, strengthen the existing Ledger banner so the first screen communicates conflict precedence, mandatory workflow, and the current checkpoint boundary.

```markdown
> **THE LEDGER IS LAW** — Single source of truth for all agents, humans, and reviewers.
> If repository instructions conflict, this Ledger wins. Read it before any developmental cycle.
> Developmental work must follow QRSPI: `.cursor/qrspi/` playbooks, with artifacts under `thoughts/qrspi/`.
> QRSPI autonomy does not authorize agents to complete Human-in-the-Loop product checkpoints.
```

Keep the existing `Last updated`, `Current phase`, `Checkpoint status`, and `Pre-merge gate` lines. Add or preserve a nearby status line such as:

```markdown
**Task workflow:** QRSPI mandatory for developmental tasks; docs-only/process tasks still record artifacts when run through QRSPI.
```

#### 2. README discovery pointer
**File**: `README.md`  
**Action**: modify

In the opening "read first" area, keep the Ledger pointer and add a task-process pointer.

```markdown
Read `architecture_and_roadmap.md` first. The Ledger is the source of truth and wins if instructions conflict.

For developmental work, follow QRSPI:

- Playbooks: `.cursor/qrspi/`
- Artifacts: `thoughts/qrspi/`
- Current law: `architecture_and_roadmap.md`
```

Do not add implementation instructions for the gateway or change runtime command examples beyond documentation pointers.

### Verification

#### Automated
- [x] `rg -n "THE LEDGER IS LAW|Ledger wins|wins if instructions conflict|QRSPI|\\.cursor/qrspi|thoughts/qrspi" architecture_and_roadmap.md README.md` shows Ledger precedence, mandatory QRSPI, playbook path, and artifact path.
- [x] `git diff -- app/proxy/interceptor.py` is empty.

#### Manual
- [x] Starting from `README.md`, a reader can identify `architecture_and_roadmap.md` as the conflict winner and `.cursor/qrspi/` as the required workflow. — autonomous: verified via rg output above
- [x] Starting from `architecture_and_roadmap.md`, a reader sees that QRSPI autonomy does not override human product checkpoints. — autonomous: verified via banner text in rg output

---

## Phase 2: Mandatory QRSPI Operational Protocol

### Changes

#### 1. Ledger operational protocol
**File**: `architecture_and_roadmap.md`  
**Action**: modify

Replace the current generic "Operational Protocol (Every Developmental Cycle)" section with "Operational Protocol - QRSPI Is Mandatory". Preserve the existing human checkpoint concepts, but make QRSPI the canonical workflow.

```markdown
## 5. Operational Protocol - QRSPI Is Mandatory

Every developmental task follows QRSPI unless the Ledger explicitly defines a narrower fast path.

| Stage | Purpose | Allowed inputs | Output / gate |
|-------|---------|----------------|---------------|
| 1. Question | Neutralize the task into research questions | User task + Ledger | `task.md`, `questions.md` |
| 2. Research | Gather codebase facts only | `questions.md`, Ledger | `research.md` |
| 3. Design | Choose the implementation direction | `task.md`, `questions.md`, `research.md`, Ledger | `design.md` with autonomous decisions |
| 4. Structure | Split into independently verifiable slices | `design.md`, `research.md`, Ledger | `structure.md` |
| 5. Plan | Expand slices into tactical implementation steps | `structure.md`, `design.md`, `research.md`, Ledger | `plan.md` |
| 6. Worktree | Create isolation boundary | QRSPI artifacts | isolated branch/worktree; no implementation |
| 7. Implement | Execute the checked plan one phase at a time | `plan.md` first | code/docs changes, verification, commits |
| 8. PR | Present the verified change | `design.md`, `plan.md`, diff, logs | PR referencing Ledger and artifacts |
```

Add the autonomous/context-isolation rules immediately after the table.

```markdown
### Autonomous QRSPI

QRSPI does not wait for process approval. When a stage exposes choices, the agent chooses the option best grounded in the Ledger, research, and existing code, records the rationale in the artifact, and proceeds.

### Context Isolation

Each stage runs in fresh context and receives only its allowed artifact inputs. Disk artifacts under `thoughts/qrspi/` are the API between stages.
```

#### 2. Human product checkpoint exception
**File**: `architecture_and_roadmap.md`  
**Action**: modify

In the same section, add a subsection that preserves the current checkpoint rules in explicit opposition to process autonomy.

```markdown
### Product Learning Checkpoints Are Not Automated

Agents may scaffold, document, validate contracts, and add tests around Human-in-the-Loop checkpoints. Agents must never complete a block marked:

```text
TODO: Human Hands-On Implementation
```

For Checkpoint #1, `app/proxy/interceptor.py` remains `blocked_on_human` until the human fills the implementation.
```

If nesting fenced code blocks becomes awkward, use an indented text block for the TODO phrase.

### Verification

#### Automated
- [x] `rg -n "Operational Protocol.*QRSPI|Question|Research|Design|Structure|Plan|Worktree|Implement|PR|Autonomous QRSPI|Context Isolation|AUTONOMOUS_MODE|CONTEXT_ISOLATION|TODO: Human Hands-On Implementation" architecture_and_roadmap.md` confirms the full stage chain, autonomy rule, isolation rule, and checkpoint boundary.
- [x] `git diff -- app/proxy/interceptor.py app/api/v1/chat.py tests/test_interceptor_contract.py tests/test_proxy_routing.py` is empty.

#### Manual
- [x] Ledger §5 reads as the complete task workflow for future development. — autonomous: verified via section 5 table and subsections
- [x] The section explicitly says process approval waits are removed while product checkpoint TODOs remain human-owned. — autonomous: verified via Autonomous QRSPI and Product Learning Checkpoints subsections

---

## Phase 3: Step 6 Actions-vs-Dashboard Clarification

### Changes

#### 1. Ledger Step 6 wording
**File**: `architecture_and_roadmap.md`  
**Action**: modify

In §0 near Step 6 and branch protection language, clarify that the GitHub Actions check proves the automated suite and quiz generation, while the dashboard/local CLI handles human comprehension practice or pass state.

```markdown
### How Step 6 is tracked

The GitHub Actions status check is named `Governance Steps 1-6`. It runs the automated suite and verifies Step 6 quiz generation.

Actions does not grade the human. The human comprehension pass happens in the dashboard before Step 7 Approve / Approve & Merge unlocks. Local practice is available with:

```bash
ai-guardrail quiz --root .. --skip-llm
```

The dashboard pass threshold is >=80%.
```

Use `≥80%` or `>=80%` consistently with the surrounding document; prefer preserving the document's existing style if one is already dominant.

#### 2. README governance wording
**File**: `README.md`  
**Action**: modify

Where the README lists the governance suite, name the status check and describe the quiz split.

```markdown
- GitHub Actions check: `Governance Steps 1-6` runs AST, OWASP/security, fuzz, Big-O, copyright, and Step 6 quiz generation.
- Dashboard Step 7: the human reads the study guide, passes the Step 6 quiz at >=80%, then Approve / Approve & Merge unlocks.
```

Update the local command comment:

```bash
ai-guardrail quiz --root .. --skip-llm   # local practice; Actions does not grade the human
```

#### 3. Setup governance wording
**File**: `SETUP_GOVERNANCE.md`  
**Action**: modify

In the branch protection, local dry-run, and PR flow sections, use the exact check name and clarify generated evidence vs human pass.

```markdown
Require the status check named `Governance Steps 1-6`.

The check proves automated Steps 1-5 plus Step 6 quiz generation. It does not grade the human quiz attempt.
```

In the PR flow:

```markdown
1. GitHub Actions runs `Governance Steps 1-6`.
2. Step 6 generates the beginner study guide and quiz pack.
3. The dashboard receives the report.
4. The reviewer studies the guide and passes the dashboard quiz at >=80%.
5. Step 7 Approve / Approve & Merge unlocks.
```

### Verification

#### Automated
- [x] `rg -n "Governance Steps 1.?6|quiz generation|does not grade|Actions does not grade|dashboard.*80|>=80|Approve|Approve & Merge|ai-guardrail quiz" architecture_and_roadmap.md README.md SETUP_GOVERNANCE.md` shows consistent CI-vs-human wording.
- [x] `git diff -- app/proxy/interceptor.py app/api/v1/chat.py tests/test_interceptor_contract.py tests/test_proxy_routing.py` is empty.

#### Manual
- [x] The docs do not imply GitHub Actions grades the human quiz attempt. — autonomous: verified via "Actions does not grade" / "does not grade the human" wording
- [x] A new contributor can tell that branch protection requires `Governance Steps 1-6`, while the dashboard separately gates Approve / Approve & Merge. — autonomous: verified via SETUP_GOVERNANCE §2 and §6

---

## Phase 4: Layout, Branch Protection, and Guardrail Consistency

### Changes

#### 1. Ledger target repository layout
**File**: `architecture_and_roadmap.md`  
**Action**: modify

In the target repository tree, add the QRSPI playbook and artifact paths plus setup governance doc.

```text
├── SETUP_GOVERNANCE.md                  # Human setup for governance CI + dashboard
├── .cursor/
│   └── qrspi/                           # QRSPI playbooks, autonomy, context isolation
├── thoughts/
│   └── qrspi/                           # QRSPI artifacts per task
```

Keep the existing gateway, governance, and dashboard tree entries.

#### 2. Ledger non-negotiable guardrails
**File**: `architecture_and_roadmap.md`  
**Action**: modify

Add guardrail bullets for mandatory QRSPI, fresh context, exact branch-protection check name, and comprehension pass.

```markdown
- Developmental work must use QRSPI and store artifacts under `thoughts/qrspi/`.
- Each QRSPI stage must run with fresh context and only its allowed artifact inputs.
- QRSPI process gates are autonomous; Human-in-the-Loop product checkpoints are not.
- No merge to `main` without the `Governance Steps 1-6` status check once branch protection is enabled.
- Step 7 review actions require the dashboard comprehension quiz pass at >=80%.
```

Merge these with existing guardrails instead of duplicating near-identical bullets.

#### 3. README and setup branch-protection consistency
**File**: `README.md`  
**Action**: modify

Add or update references so root-level setup points to `SETUP_GOVERNANCE.md`, Ledger §11, and the exact check name `Governance Steps 1-6`.

**File**: `SETUP_GOVERNANCE.md`  
**Action**: modify

Confirm every branch-protection instruction uses `Governance Steps 1-6` exactly. Avoid generic "AI Guardrail check" wording where the human needs the GitHub status-check name.

### Verification

#### Automated
- [x] `rg -n "SETUP_GOVERNANCE|\\.cursor/qrspi|thoughts/qrspi|Governance Steps 1.?6|branch protection|Non-Negotiable|fresh context|allowed artifact inputs" architecture_and_roadmap.md README.md SETUP_GOVERNANCE.md` confirms discoverability, branch protection wording, and guardrail consistency.
- [x] `git diff -- app/proxy/interceptor.py app/api/v1/chat.py tests/test_interceptor_contract.py tests/test_proxy_routing.py` is empty.

#### Manual
- [x] Ledger §7 shows both QRSPI paths and `SETUP_GOVERNANCE.md`. — autonomous: verified via layout tree in rg output
- [x] Ledger §8 connects QRSPI law, branch protection, and human checkpoint preservation without weakening any existing runtime guardrail. — autonomous: verified via guardrails 2-4, 6, 12-13

---

## Phase 5: Human Checkpoint Preservation and Final Doc Coherence

### Changes

#### 1. Human checkpoint reaffirmation
**File**: `architecture_and_roadmap.md`  
**Action**: modify

Review the Ledger for every autonomy/process statement added in Phases 1-4. Ensure nearby wording preserves this invariant:

```markdown
Autonomous QRSPI removes process approval waits. It does not permit agents to complete product learning checkpoints or remove `TODO: Human Hands-On Implementation` blocks.
```

Confirm §6 still says:

```markdown
**File:** `app/proxy/interceptor.py`
**Status:** `blocked_on_human`
```

and still forbids agents from silently completing the function.

#### 2. README checkpoint reminder
**File**: `README.md`  
**Action**: modify

Where README introduces workflow or current status, add a concise checkpoint reminder.

```markdown
Current product checkpoint: `app/proxy/interceptor.py` remains human-owned and `blocked_on_human`; QRSPI agents must not implement it.
```

#### 3. Setup governance checkpoint reminder
**File**: `SETUP_GOVERNANCE.md`  
**Action**: modify

In the human/manual setup area, add a short note that governance and QRSPI do not replace the resume-defense checkpoint.

```markdown
Governance and QRSPI enforce process. They do not auto-complete Human-in-the-Loop product checkpoints such as `app/proxy/interceptor.py`.
```

#### 4. Final scope and artifact checks
**File**: documentation only  
**Action**: verify

Confirm the implementation touched only:

- `architecture_and_roadmap.md`
- `README.md`
- `SETUP_GOVERNANCE.md`
- QRSPI artifacts/docs already in scope, if needed for the QRSPI run

Do not edit:

- `app/proxy/interceptor.py`
- `app/api/v1/chat.py`
- `tests/test_interceptor_contract.py`
- `tests/test_proxy_routing.py`
- governance CLI, dashboard code, or workflows

### Verification

#### Automated
- [ ] `rg -n "blocked_on_human|app/proxy/interceptor.py|Never auto-complete|must not implement|Human-in-the-Loop|Autonomous Mode|Autonomous QRSPI|product checkpoint|TODO: Human Hands-On Implementation" architecture_and_roadmap.md README.md SETUP_GOVERNANCE.md` confirms boundary text.
- [ ] `git diff --name-only` contains only `architecture_and_roadmap.md`, `README.md`, `SETUP_GOVERNANCE.md`, and QRSPI artifact/doc files.
- [ ] `git diff -- app/proxy/interceptor.py app/api/v1/chat.py tests/test_interceptor_contract.py tests/test_proxy_routing.py` is empty.
- [ ] `git status --short -- .cursor/qrspi thoughts/qrspi/README.md` is empty after the final commit, proving required QRSPI playbooks and artifact README are committed.

#### Manual
- [ ] Every autonomy statement is paired with or near the product-checkpoint exception.
- [ ] The final docs consistently say: Ledger wins; QRSPI is mandatory; Actions generates Step 6 quiz evidence; dashboard/local practice handles human comprehension; `app/proxy/interceptor.py` remains untouched.

---

## Autonomous Assumptions

- **Open question resolved: whether to read or edit runtime files.** Do not read or edit runtime implementation files during implementation. Use `git diff -- <paths>` to prove they remain unchanged.
- **Open question resolved: whether to rename the CI check.** Keep the check name `Governance Steps 1-6`; documentation clarifies what it proves rather than renaming existing workflow behavior.
- **Open question resolved: how to handle branch protection enforcement.** Documentation can require the setting and name the exact check, but the implementation does not attempt to change GitHub repository settings.
- **Open question resolved: how much target-branch wording to restore.** Restore the concepts from the stronger target-branch docs while preserving current Ledger governance details; do not wholesale replace sections.
- **Open question resolved: whether QRSPI autonomy can complete product TODOs.** It cannot. Autonomy applies only to process approval waits and decision recording.
- **Open question resolved: what must be committed.** The implementation branch must include committed `.cursor/qrspi/**` playbooks, `thoughts/qrspi/README.md`, and this QRSPI run's artifacts. If those files are already tracked and unchanged, verify with `git status --short -- .cursor/qrspi thoughts/qrspi/README.md`; otherwise stage and commit them with the docs-only change.

## Deviations from `structure.md`

None. The phase order, file scope, checkpoint boundary, and verification focus match `structure.md`.
