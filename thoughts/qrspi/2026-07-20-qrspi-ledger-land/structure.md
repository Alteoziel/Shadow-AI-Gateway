# Structure Outline

## Approach

Implement this as a documentation-only process-law update. The Ledger becomes the canonical place for mandatory QRSPI, conflict precedence, autonomous process flow, Step 6 semantics, and the continuing human-owned product checkpoint boundary; README and setup docs point to and reinforce that law without changing runtime gateway behavior.

## Phase 1: Ledger Law and Workflow Discovery

Make the repository entry points say, end-to-end, that the Ledger is law and QRSPI is the required workflow for developmental tasks. This gives future agents and humans a clear first stop before they touch code.

**Files**: `architecture_and_roadmap.md`, `README.md`

**Key changes**:
- `LedgerLaw { source: "architecture_and_roadmap.md"; precedence: "wins_on_conflict"; workflow: "QRSPI" }` - documented process contract.
- `TaskWorkflowPointer { playbooks: ".cursor/qrspi/"; artifacts: "thoughts/qrspi/" }` - README discovery contract.
- No runtime function signatures change.

**Verify**: `rg -n "THE LEDGER IS LAW|Ledger wins|QRSPI|\\.cursor/qrspi|thoughts/qrspi" architecture_and_roadmap.md README.md` shows the law, conflict precedence, workflow pointer, and artifact pointer.

---

## Phase 2: Mandatory QRSPI Operational Protocol

Replace the generic developmental-cycle language with a Ledger-level protocol that lists the QRSPI stages, the fresh-context requirement, autonomous stage behavior, and the product-checkpoint exception. This phase is valuable on its own because it governs future work even before other docs are polished.

**Files**: `architecture_and_roadmap.md`

**Key changes**:
- `QRSPIStage { name: string; allowedInputs: string; output: string; verificationGate: string }` - documented stage table shape.
- `AutonomousProcessRule { waitForApproval: false; chooseGroundedOption: true; recordRationale: true }` - documented QRSPI autonomy rule.
- `HumanCheckpointBoundary { agentsMayScaffold: true; agentsMayCompleteTodo: false }` - documented exception for `TODO: Human Hands-On Implementation`.

**Verify**: `rg -n "Operational Protocol.*QRSPI|Question|Research|Design|Structure|Plan|Worktree|Implement|PR|AUTONOMOUS_MODE|CONTEXT_ISOLATION|TODO: Human Hands-On Implementation" architecture_and_roadmap.md` confirms the full stage chain and boundary language are present.

---

## Phase 3: Step 6 Actions-vs-Dashboard Clarification

Clarify the comprehension gate across the Ledger, README, and setup guide so the named GitHub Actions check proves automated Steps 1-6 plus quiz generation, while the human quiz pass remains a dashboard/local-practice concept that unlocks Step 7 actions.

**Files**: `architecture_and_roadmap.md`, `README.md`, `SETUP_GOVERNANCE.md`

**Key changes**:
- `ComprehensionGateContract { ciCheckName: "Governance Steps 1-6"; ciEvidence: "quiz_generation"; humanPassLocation: "dashboard"; passThreshold: ">=80%" }` - documentation contract.
- `LocalPracticeCommand = "ai-guardrail quiz --root .. --skip-llm"` - setup/README command note, explicitly not Actions grading.
- No governance CLI, dashboard route, or workflow behavior changes.

**Verify**: `rg -n "Governance Steps 1.?6|quiz generation|does not grade|dashboard.*80|Approve|Approve & Merge|ai-guardrail quiz" architecture_and_roadmap.md README.md SETUP_GOVERNANCE.md` shows consistent CI-vs-human wording.

---

## Phase 4: Layout, Branch Protection, and Guardrail Consistency

Update structural documentation so QRSPI assets, setup instructions, and required checks are visible in the Ledger's repository map and non-negotiable guardrails. This ties the process law to the files and GitHub setting a future implementer must inspect.

**Files**: `architecture_and_roadmap.md`, `README.md`, `SETUP_GOVERNANCE.md`

**Key changes**:
- `RepositoryLayoutEntry { path: ".cursor/qrspi/"; role: "QRSPI playbooks" }` - add to target layout.
- `RepositoryLayoutEntry { path: "thoughts/qrspi/"; role: "QRSPI artifacts" }` - add to target layout.
- `RequiredStatusCheck = "Governance Steps 1-6"` - use exact check name in branch-protection docs.

**Verify**: `rg -n "SETUP_GOVERNANCE|\\.cursor/qrspi|thoughts/qrspi|Governance Steps 1.?6|branch protection|Non-Negotiable" architecture_and_roadmap.md README.md SETUP_GOVERNANCE.md` confirms discoverability and required-check wording.

---

## Phase 5: Human Checkpoint Preservation and Final Doc Coherence

Do a final documentation pass that keeps every autonomy statement paired with the product-checkpoint exception and confirms no product behavior changed. This slice protects the active `app/proxy/interceptor.py` checkpoint while making the new QRSPI rules enforceable by prose.

**Files**: `architecture_and_roadmap.md`, `README.md`, `SETUP_GOVERNANCE.md`

**Key changes**:
- `CheckpointScope { file: "app/proxy/interceptor.py"; status: "blocked_on_human"; forbiddenAgentAction: "complete_checkpoint" }` - reaffirm existing boundary.
- `NoProductBehaviorChange { runtimeFilesTouched: false; interceptorTodoPreserved: true }` - implementation invariant.
- No changes to `app/proxy/interceptor.py`, `app/api/v1/chat.py`, `tests/test_interceptor_contract.py`, or `tests/test_proxy_routing.py`.

**Verify**: `rg -n "blocked_on_human|app/proxy/interceptor.py|Never auto-complete|Human-in-the-Loop|Autonomous Mode|product checkpoint" architecture_and_roadmap.md README.md SETUP_GOVERNANCE.md` confirms boundary text; `git diff -- app/proxy/interceptor.py app/api/v1/chat.py tests/test_interceptor_contract.py tests/test_proxy_routing.py` is empty.

## Testing Checkpoints

- After Phase 1, a reader starting from the root README or Ledger can identify the Ledger as the conflict winner and QRSPI as mandatory.
- After Phase 2, the Ledger contains the complete QRSPI stage sequence, autonomy rule, context-isolation rule, and human checkpoint exception.
- After Phase 3, all public setup docs distinguish the `Governance Steps 1-6` Actions check from the human quiz pass on the dashboard.
- After Phase 4, the repository layout and guardrails mention QRSPI paths and the exact branch-protection check name.
- After Phase 5, documentation remains consistent and runtime checkpoint files are untouched.
