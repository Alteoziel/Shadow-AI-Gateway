# Structure Outline

## Approach

Add a standalone scrub checkpoint scaffold that mirrors the existing human-owned interceptor pattern but remains completely disconnected from Phase 1 routing. Verify the scaffold by asserting the placeholder contract, the latency-budget marker, Ledger path updates, and absence of scrub imports from chat/interceptor files.

## Phase 1: Scrub Package Scaffold

Create an importable `app.scrub` package with lightweight contracts and a single human-owned pipeline entrypoint.

**Files**: `app/scrub/__init__.py`, `app/scrub/types.py`, `app/scrub/pipeline.py`

**Key changes**:

- `SCRUB_LATENCY_BUDGET_MS: int` - documents the sub-100ms budget.
- `ScrubFinding` - typed placeholder for future sensitive-data findings.
- `ScrubRequest` - typed input contract carrying text and metadata.
- `ScrubResult` - typed output contract for sanitized text, findings, and elapsed time.
- `async def scrub_prompt(request: ScrubRequest) -> ScrubResult` - human checkpoint stub that raises `NotImplementedError`.

**Verify**: import `app.scrub`; pytest confirms the async stub raises and the budget is documented.

---

## Phase 2: Ledger and Latency Harness Stub

Record the Phase 2 checkpoint path in the Ledger and add tests that protect the scaffold boundaries.

**Files**: `architecture_and_roadmap.md`, `tests/test_scrub_pipeline_contract.py`

**Key changes**:

- Replace Phase 2 checkpoint file `TBD` references with `app/scrub/pipeline.py`.
- Keep Phase 2 phase status `not_started`.
- Keep Phase 2 checkpoint status `not_started` and Checkpoint #1 status `blocked_on_human`.
- `test_scrub_pipeline_stub_raises_not_implemented()` - asserts the human checkpoint remains unimplemented.
- `test_scrub_latency_budget_is_documented()` - asserts the budget is 100ms and named in the pipeline source.
- `test_scrub_not_wired_into_phase1_route_or_interceptor()` - confirms no scrub import in chat/interceptor.

**Verify**: `pytest tests/test_scrub_pipeline_contract.py tests/test_interceptor_contract.py tests/test_proxy_routing.py` passes.

---

## Phase 3: QRSPI and PR Draft Artifacts

Complete the required workflow artifacts and draft PR body without creating or merging a PR directly.

**Files**: `thoughts/qrspi/2026-07-20-phase2-scrub-stub/*`, `.pr-drafts/agent9.md`, `/tmp/pr-drafts/agent9.md`

**Key changes**:

- QRSPI artifacts record stage inputs, decisions, implementation progress, verification, and PR context.
- PR draft references The Ledger and the QRSPI artifact directory.

**Verify**: `git diff --name-only origin/cursor/qrspi-ledger-land-5e0d...HEAD` shows only scaffold, docs, tests, and artifacts for this task.

## Testing Checkpoints

- After Phase 1, `app.scrub` imports and `scrub_prompt(...)` remains human-owned.
- After Phase 2, the focused pytest suite passes and source search confirms no scrub wiring.
- After Phase 3, the branch contains the PR draft files and QRSPI artifacts needed for review.
