# Design Discussion

## Current State

This repository already has the core QRSPI workflow scaffold: stage playbooks, helper-agent templates, artifact directory conventions, Autonomous Mode, and Context Isolation. The canonical stage sequence is Question -> Research -> Design -> Structure -> Plan -> Worktree -> Implement -> PR, and the QRSPI README defines the allowed artifact inputs per stage, including Research receiving only `questions.md` and Design receiving `task.md`, `questions.md`, and `research.md`. `.cursor/qrspi/README.md:1-19`

The stage playbooks already point agents toward autonomous execution and say the Ledger is law. The Design playbook specifically requires 3-5 design questions, options, chosen answers, and a written `design.md`. `.cursor/qrspi/3_design.md:6-10`, `.cursor/qrspi/3_design.md:16-30`

Autonomous Mode is already present and explicitly disables human approval waits inside QRSPI while preserving product Human-in-the-Loop checkpoints. `.cursor/qrspi/AUTONOMOUS_MODE.md:1-17`, `.cursor/qrspi/AUTONOMOUS_MODE.md:62-66`

Context Isolation is already present and requires fresh stage runners, file-scoped inputs, and disk artifacts as the API between stages. `.cursor/qrspi/CONTEXT_ISOLATION.md:1-24`

The Ledger is the repository's single source of truth and currently tracks Phase 1 Crawl with Checkpoint #1 blocked on human implementation in `app/proxy/interceptor.py`. `architecture_and_roadmap.md:1-9`

The current Ledger also documents the governance gate, including Step 6 as a beginner study guide and quiz with an 80% pass bar on the dashboard or local CLI practice. `architecture_and_roadmap.md:39-49`

The human checkpoint boundary is clear in the Ledger: agents may scaffold and validate, but must never auto-complete human checkpoint implementations. `architecture_and_roadmap.md:210-225`

The active human checkpoint is `app/proxy/interceptor.py`, where the permitted scope is validation and normalization only, while scrubbing and DB writes remain out of scope. The Ledger also requires the chat route to invoke the interceptor before provider streaming. `architecture_and_roadmap.md:228-248`

Documentation already introduces the governance suite in the root README, points readers to the Ledger, and lists local commands such as `ai-guardrail run` and `ai-guardrail quiz`. `README.md:1-22`

Setup documentation already says branch protection must require the `Governance Steps 1-6` check and that the workflow is advisory until enabled. `SETUP_GOVERNANCE.md:1-17`

The implementation distinguishes generated quiz evidence in CI from the human quiz pass in the dashboard: Step 6 generation returns `passed=True` once the quiz pack is generated, while the dashboard enforces the human pass before approve or merge. `governance/governance/steps/comprehension_gate.py:716-723`, `dashboard/src/app/api/reviews/[id]/route.ts:96-120`

The scoped branch comparison found that the target branch had stronger Ledger wording for "THE LEDGER IS LAW", mandatory QRSPI, task workflow status, context isolation, autonomous gates, and the Actions-vs-quiz distinction. `origin/cursor/architecture-ledger-bf7f:architecture_and_roadmap.md:1-17`, `origin/cursor/architecture-ledger-bf7f:architecture_and_roadmap.md:218-282`

## Desired End State

Land a documentation and process-law update that makes QRSPI mandatory for future developmental work and makes the Ledger's precedence explicit.

The Ledger should clearly say that QRSPI is the required workflow for developmental tasks, that the Ledger wins when instructions conflict, and that Autonomous Mode removes QRSPI approval waits without authorizing agents to fill human product checkpoints.

Root and setup documentation should clearly point future agents and humans to the QRSPI workflow, artifact directory, Ledger, and branch-protection setup.

The Step 6 comprehension language should be unambiguous: GitHub Actions runs the `Governance Steps 1-6` job and proves the automated suite plus quiz generation, but the actual human quiz pass gates dashboard Actions such as Approve and Approve & Merge.

No product behavior should change in this task. In particular, `app/proxy/interceptor.py` must remain a human-owned checkpoint and must not be implemented here.

Verification should be documentation-focused: confirm the expected files contain the process-law language, quiz-vs-Actions clarification, and checkpoint boundary language; no runtime proxy behavior should be changed.

## Design Questions

1. **Where should QRSPI law be anchored?**
   - Option A: Keep QRSPI law only in `.cursor/qrspi/README.md`.
     - Trade-off: Localizes workflow details, but weakens the Ledger's single-source-of-truth role.
   - Option B: Put canonical law in the Ledger and keep `.cursor/qrspi/` as the operational playbook.
     - Trade-off: Duplicates a little process language, but matches the repository's "Ledger is law" model.
   - Option C: Put only a short pointer in the Ledger and rely on individual stage files.
     - Trade-off: Minimizes Ledger size, but future agents may miss mandatory workflow constraints.

2. **How should Step 6 be described relative to GitHub Actions?**
   - Option A: Say Actions "passes Step 6" without qualification.
     - Trade-off: Simple wording, but misleading because Actions generates quiz material while dashboard grading enforces human comprehension.
   - Option B: Say Actions runs Steps 1-6 and generates Step 6 evidence; the dashboard gates Approve/Merge on the human quiz pass.
     - Trade-off: Slightly longer, but exactly matches the implementation and setup flow.
   - Option C: Rename CI to Steps 1-5 to avoid ambiguity.
     - Trade-off: Avoids one confusion point, but diverges from existing workflow naming and branch protection guidance.

3. **How should human checkpoint boundaries be represented while adding autonomous QRSPI?**
   - Option A: Mention autonomy only and rely on existing checkpoint docs.
     - Trade-off: Short, but risks agents interpreting autonomy as permission to fill product TODOs.
   - Option B: Pair every autonomy statement with the explicit product-checkpoint exception.
     - Trade-off: Repetitive, but safest for the resume-defense and human-learning constraints.
   - Option C: Move checkpoint boundaries out of the Ledger into code comments only.
     - Trade-off: Keeps docs shorter, but contradicts the Ledger-first operating model.

4. **How much target-branch wording should be restored?**
   - Option A: Copy the target branch sections verbatim.
     - Trade-off: Fast and explicit, but may overwrite newer current Ledger details.
   - Option B: Reintroduce the target branch's missing concepts while preserving current governance and checkpoint content.
     - Trade-off: Requires careful editing, but keeps the best current and target-branch facts.
   - Option C: Avoid target-branch concepts and only polish current text.
     - Trade-off: Low risk, but fails to land the stronger QRSPI-as-law language found by research.

5. **What is the implementation scope for this QRSPI task?**
   - Option A: Documentation and QRSPI artifacts only.
     - Trade-off: Narrow and aligned with the task, but leaves product code untouched.
   - Option B: Documentation plus governance/dashboard code changes.
     - Trade-off: Could strengthen enforcement, but research shows the core quiz/dashboard distinction already exists.
   - Option C: Documentation plus `interceptor.py` implementation.
     - Trade-off: Would be product progress, but directly violates the active human checkpoint boundary.

## Autonomous Decisions

1. **Q: Where should QRSPI law be anchored? -> Chosen: Option B.**
   - The Ledger is already the single source of truth, so mandatory QRSPI and conflict precedence belong there, with `.cursor/qrspi/` remaining the operational playbook. `architecture_and_roadmap.md:1-9`, `.cursor/qrspi/README.md:1-19`

2. **Q: How should Step 6 be described relative to GitHub Actions? -> Chosen: Option B.**
   - The code and docs already split CI quiz generation from dashboard quiz grading; the documentation should use that same model instead of implying the human is graded in Actions. `governance/governance/steps/comprehension_gate.py:716-723`, `dashboard/src/app/api/reviews/[id]/route.ts:96-120`, `SETUP_GOVERNANCE.md:75-89`

3. **Q: How should human checkpoint boundaries be represented while adding autonomous QRSPI? -> Chosen: Option B.**
   - Autonomous QRSPI only removes process approval waits. It must repeatedly preserve the human-owned product checkpoint rule because the active checkpoint remains blocked on human work. `.cursor/qrspi/AUTONOMOUS_MODE.md:62-66`, `architecture_and_roadmap.md:210-225`, `architecture_and_roadmap.md:228-248`

4. **Q: How much target-branch wording should be restored? -> Chosen: Option B.**
   - Research shows the target branch had stronger law language, but the current Ledger has useful governance-gate detail. The right move is to merge the concepts, not wholesale replace current sections. `origin/cursor/architecture-ledger-bf7f:architecture_and_roadmap.md:1-17`, `origin/cursor/architecture-ledger-bf7f:architecture_and_roadmap.md:218-282`, `architecture_and_roadmap.md:39-65`

5. **Q: What is the implementation scope for this QRSPI task? -> Chosen: Option A.**
   - The task is to land QRSPI and Ledger law, clarify quiz vs Actions, and preserve checkpoint boundaries. No product code should change, and `app/proxy/interceptor.py` must never be implemented by this work. `architecture_and_roadmap.md:210-225`, `app/proxy/interceptor.py:5-39`

## Patterns to Follow

Use the existing QRSPI stage model and artifact API: each downstream stage should consume only its allowed files, and docs should preserve the Question -> Research -> Design -> Structure -> Plan -> Worktree -> Implement -> PR sequence. `.cursor/qrspi/README.md:10-19`

Keep QRSPI Autonomous Mode scoped to process flow. Autonomy means choose grounded options and proceed through QRSPI; it does not mean bypassing Human-in-the-Loop product checkpoints. `.cursor/qrspi/AUTONOMOUS_MODE.md:1-17`, `.cursor/qrspi/AUTONOMOUS_MODE.md:62-66`

Follow Context Isolation as a hard process constraint: fresh stage runners, file-scoped inputs, and disk artifacts as the only bridge between stages. `.cursor/qrspi/CONTEXT_ISOLATION.md:1-24`

Preserve the governance model where Actions runs the named `Governance Steps 1-6` workflow, branch protection requires that check, and the dashboard separately locks review/merge until comprehension passes. `.github/workflows/ai-guardrail.yml:1-15`, `SETUP_GOVERNANCE.md:9-17`, `dashboard/src/app/api/reviews/[id]/route.ts:96-145`

Keep beginner-friendly comprehension language: the quiz exists to teach and verify understanding, with explanations on wrong answers. `architecture_and_roadmap.md:39-50`

Keep the active human checkpoint language explicit in both law and scope. Agents may validate contracts around `app/proxy/interceptor.py`, but must not fill the TODO or remove the human checkpoint. `architecture_and_roadmap.md:210-225`, `architecture_and_roadmap.md:228-248`

## Patterns NOT to Follow

Do not leave QRSPI only as hidden Cursor playbook documentation; research shows the target branch made QRSPI an explicit Ledger-level operational protocol. `origin/cursor/architecture-ledger-bf7f:architecture_and_roadmap.md:218-282`

Do not describe the Step 6 quiz as a GitHub Actions human grading event. Actions proves suite execution and quiz generation; dashboard actions are what the human quiz unlocks. `governance/governance/cli.py:90-103`, `dashboard/src/components/ReviewPanel.tsx:443-479`

Do not treat dashboard availability as a CI blocker unless future requirements explicitly change; reporter behavior is currently non-blocking for dashboard POST failures. `governance/governance/reporters/github.py:116-137`

Do not broaden this task into gateway implementation, scrubbing, DB writes, Terraform, or product checkpoint completion. `architecture_and_roadmap.md:228-246`

## Design Decisions

1. **Ledger-first process law**: Add or restore explicit "Ledger is law" conflict precedence and mandatory QRSPI workflow language in `architecture_and_roadmap.md` because the Ledger is the repository's governing source.

2. **QRSPI as mandatory developmental workflow**: Document the eight QRSPI stages in the Ledger and reference `.cursor/qrspi/` plus `thoughts/qrspi/` so future agents can discover both playbooks and artifacts.

3. **Autonomous QRSPI with checkpoint exception**: State that QRSPI stages do not wait for human approval, but Human-in-the-Loop product checkpoint TODOs remain human-owned and may not be auto-completed.

4. **Quiz vs Actions clarification**: Use consistent wording in Ledger, README, and setup docs: GitHub Actions runs `Governance Steps 1-6` and generates Step 6 material; the dashboard grades the human quiz and gates Approve / Approve & Merge.

5. **Preserve existing governance implementation**: No code changes are required for the quiz/dashboard split because research found the CLI, pipeline, dashboard store, API route, and UI already enforce that distinction.

6. **Documentation-only implementation slice**: Downstream implementation should edit process docs and QRSPI artifacts only, not runtime gateway files.

## What We're NOT Doing

We are not implementing `app/proxy/interceptor.py`.

We are not removing the `NotImplementedError` checkpoint or changing tests that assert the checkpoint remains human-owned.

We are not implementing Phase 2 scrubbing, Phase 3 database logging, or Phase 4 Docker/Terraform core work.

We are not changing dashboard runtime behavior unless later planning discovers a documentation mismatch that cannot be fixed in prose.

We are not renaming the GitHub Actions job away from `Governance Steps 1-6`.

We are not making dashboard POST failures fail CI in this task.

## Open Risks

Branch protection is still human setup. Documentation can instruct the user to require `Governance Steps 1-6`, but cannot enforce repository settings by itself. `SETUP_GOVERNANCE.md:9-17`

The research did not inspect a deployed dashboard instance, so runtime deployment configuration is outside the current design basis. `dashboard/src/app/api/reviews/[id]/route.ts:25-145`, `dashboard/src/components/ReviewPanel.tsx:190-479`

Merging target-branch concepts into the current Ledger requires careful editing so the stronger QRSPI law language does not accidentally delete current governance details. `origin/cursor/architecture-ledger-bf7f:architecture_and_roadmap.md:1-17`, `architecture_and_roadmap.md:39-65`

Because this task updates governance documentation, downstream implementation should verify terminology across README, setup docs, Ledger, and QRSPI docs to avoid future agent confusion.
