# Implementation Plan

## Overview

Prepare Phase 2 scrub checkpoint scaffolding only. The resulting branch must expose the future human-owned scrub pipeline path and budget contract while keeping all production request flow unchanged.

## Autonomous Assumptions

- Phase 2 checkpoint status stays `not_started` because this branch prepares a path but does not start or complete Phase 2.
- The human-owned scrub entrypoint should raise immediately instead of returning a pass-through result, preventing accidental production use.
- Source-inspection tests are sufficient to confirm no scrub wiring because the task explicitly forbids route/interceptor integration.

## Phase 1: Scrub Package Scaffold

### Changes

#### 1. Package exports

**File**: `app/scrub/__init__.py`  
**Action**: create

- Export `SCRUB_LATENCY_BUDGET_MS`, `ScrubFinding`, `ScrubRequest`, `ScrubResult`, and `scrub_prompt`.
- Keep `__all__` narrow.

#### 2. Type contracts

**File**: `app/scrub/types.py`  
**Action**: create

- Add dataclasses:
  - `ScrubFinding(kind: str, start: int, end: int, replacement: str, confidence: float | None = None)`
  - `ScrubRequest(text: str, metadata: Mapping[str, Any] | None = None)`
  - `ScrubResult(original_text: str, sanitized_text: str, findings: tuple[ScrubFinding, ...], elapsed_ms: float)`
- Add `ScrubAction = Literal["redact", "flag"]` only as a future contract marker if useful.
- Do not add methods that perform redaction or detection.

#### 3. Pipeline entrypoint

**File**: `app/scrub/pipeline.py`  
**Action**: create

- Add `SCRUB_LATENCY_BUDGET_MS = 100`.
- Add `async def scrub_prompt(request: ScrubRequest) -> ScrubResult`.
- Inside the function, include:
  - `TODO: Human Hands-On Implementation`
  - three cheat-sheet bullets, including sub-100ms latency budget
  - scope notes forbidding provider wiring and database work
  - `raise NotImplementedError(...)`
- Do not implement regex, NLP, tokenization, or mutation logic.

### Verification

#### Automated

- [x] `python -m pytest tests/test_scrub_pipeline_contract.py` passes.

#### Manual

- [x] autonomous: source inspection confirms `app/scrub/pipeline.py` contains the human TODO and `NotImplementedError`.

---

## Phase 2: Ledger and Latency Harness Stub

### Changes

#### 1. Focused tests

**File**: `tests/test_scrub_pipeline_contract.py`  
**Action**: create

- Assert `scrub_prompt` is async.
- Assert it raises `NotImplementedError` for a `ScrubRequest`.
- Assert `SCRUB_LATENCY_BUDGET_MS == 100`.
- Assert pipeline source mentions sub-100ms and the human TODO.
- Assert `app/api/v1/chat.py` and `app/proxy/interceptor.py` do not contain `app.scrub`, `scrub_prompt`, or `SCRUB_LATENCY_BUDGET_MS`.

#### 2. Ledger checkpoint path

**File**: `architecture_and_roadmap.md`  
**Action**: update

- Replace the Phase 2 checkpoint file from `TBD - core string substitution / regex-NLP scrubbing loop` to `` `app/scrub/pipeline.py` - core string substitution / regex-NLP scrubbing loop``.
- Replace Phase 2 progression audit checkpoint file `TBD` with `` `app/scrub/pipeline.py` ``.
- Replace Resume Defense Map Phase 2 TBD path with `` `app/scrub/pipeline.py` ``.
- Do not change Phase 2 status from `not_started`.
- Do not change Checkpoint #1 status from `blocked_on_human`.

### Verification

#### Automated

- [x] `python -m pytest tests/test_scrub_pipeline_contract.py tests/test_interceptor_contract.py tests/test_proxy_routing.py` passes.

#### Manual

- [x] autonomous: `rg "app\\.scrub|scrub_prompt|SCRUB_LATENCY_BUDGET_MS" app/api/v1/chat.py app/proxy/interceptor.py` returns no matches.
- [x] autonomous: `rg "Phase 2|Walk|app/scrub/pipeline.py|blocked_on_human" architecture_and_roadmap.md` confirms requested status/path state.

---

## Phase 3: QRSPI and PR Draft Artifacts

### Changes

#### 1. QRSPI completion artifacts

**File**: `thoughts/qrspi/2026-07-20-phase2-scrub-stub/worktree.md`  
**Action**: create

- Record branch setup from `origin/cursor/qrspi-ledger-land-5e0d`.
- Record active branch name.

**File**: `thoughts/qrspi/2026-07-20-phase2-scrub-stub/implementation.md`  
**Action**: create

- Record files changed, verification commands, and no-wiring confirmation.

**File**: `thoughts/qrspi/2026-07-20-phase2-scrub-stub/pr.md`  
**Action**: create

- Record PR title/body source summary.

#### 2. PR draft files

**File**: `.pr-drafts/agent9.md` and `/tmp/pr-drafts/agent9.md`  
**Action**: create identical draft content

- Include summary, design decisions, changes, verification, and references to Ledger plus QRSPI artifacts.

### Verification

#### Automated

- [x] `git diff --name-only origin/cursor/qrspi-ledger-land-5e0d...HEAD` includes only expected task files.

#### Manual

- [x] autonomous: PR draft files exist at both requested paths.
