# Implementation Plan

## Overview

Grow the governance Step 5 and Step 6 educational guardrails without changing gateway runtime behavior. The implementation adds FastAPI/httpx protected signatures, deterministic Phase 1 quiz questions, tests, artifacts, and PR drafts while leaving Checkpoint #1 human-owned.

## Autonomous Assumptions

- Deterministic quiz generation is the correct target because CI/local tests run with `skip_llm=True`.
- Existing `governance/tests/test_steps.py` remains the right place for focused unit coverage.
- The requested branch itself is the isolation boundary in Cursor Cloud; no separate worktree is necessary.

## Phase 1: Copyright signatures for gateway anti-patterns

### Changes

#### 1. Protected snippet database
**File**: `governance/governance/signatures/known_snippets.json`  
**Action**: modify

Add five records:

- `fastapi_sync_httpx_in_async_route`
- `httpx_async_client_per_stream_chunk`
- `hardcoded_provider_bypass`
- `checkpoint_501_catchall_mask`
- `raw_sse_bytes_without_cleanup`

Each `content` should be a realistic but compact FastAPI/httpx anti-pattern.

#### 2. Copyright test
**File**: `governance/tests/test_steps.py`  
**Action**: modify

Add `test_copyright_exact_match_fastapi_httpx_antipattern` that writes one exact new snippet to a temp `.py` file, runs `copyright_filter.run`, and expects `COPY001_EXACT` or `COPY002_SIMILAR`.

### Verification

#### Automated
- [x] `cd governance && python3 -m pytest tests/test_steps.py -k copyright` passes.

#### Manual
- [x] Signature database contains at least 5 FastAPI/httpx anti-pattern signatures. autonomous: verified with `python3 - <<'PY' ...` showing 7 total signatures and 5 new gateway signatures.

---

## Phase 2: Phase 1 comprehension quiz packs

### Changes

#### 1. Deterministic glossary and questions
**File**: `governance/governance/steps/comprehension_gate.py`  
**Action**: modify

Add glossary terms for provider, upstream provider, streaming/SSE, and HTTP 501. Add deterministic quiz questions:

- `phase1_provider_selection` (`vocabulary`)
- `phase1_provider_flow` (`how_it_works`)
- `phase1_streaming_flow` (`how_it_works`)
- `phase1_checkpoint_501` (`manual_tasks`)

The 501 question must say Checkpoint #1 is human-owned and agents must not fill `app/proxy/interceptor.py`.

#### 2. Quiz generation test
**File**: `governance/tests/test_steps.py`  
**Action**: modify

Extend `test_comprehension_generates_quiz` to assert:

- new IDs are present,
- categories include vocabulary/how_it_works/manual_tasks,
- the 501 question explanation contains `human-owned` and `app/proxy/interceptor.py`.

### Verification

#### Automated
- [x] `cd governance && python3 -m pytest tests/test_steps.py -k comprehension` passes.

#### Manual
- [x] Generated pack contains provider, streaming, and 501 questions. autonomous: verified through pytest assertions.

---

## Phase 3: QRSPI, PR drafts, and full verification

### Changes

#### 1. Stage artifacts
**File**: `thoughts/qrspi/2026-07-20-gov-copyright-quiz-packs/`  
**Action**: create/update

Add or update `worktree.md`, `implement.md`, and `pr.md`. Check off verification boxes in this `plan.md` as commands pass.

#### 2. PR draft files
**Files**: `/tmp/pr-drafts/agent7.md`, `.pr-drafts/agent7.md`  
**Action**: create

Write matching draft text with summary, tests, Ledger/QRSPI references, and explicit interceptor untouched note.

### Verification

#### Automated
- [x] `cd governance && python3 -m pytest` passes.
- [x] `cd governance && python3 -m governance.cli run --root .. --skip-fuzz --skip-llm --no-fail-on-error` completes and reports Step 6 quiz generation.
- [x] `git diff -- app/proxy/interceptor.py` is empty.

#### Manual
- [x] PR draft exists in both requested locations. autonomous: verified with `wc -l .pr-drafts/agent7.md /tmp/pr-drafts/agent7.md /workspace/.pr-drafts/agent7.md`.
- [ ] Branch pushed to `origin cursor/gov-copyright-quiz-packs-5e0d`. autonomous: verify with `git rev-parse HEAD` and `git push`.
