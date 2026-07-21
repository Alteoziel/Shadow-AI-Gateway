# Implementation Plan

## Overview

Step 3 will fuzz a real gateway pure helper without blocking on expected input-contract rejections, and Step 4 will expose a documented informational API for per-PR benchmark target injection. The interceptor checkpoint remains untouched.

## Autonomous Assumptions

- A strict pure helper may reject every deterministic boundary input and still satisfy the fuzz goal if the harness records execution and no unexpected crash.
- `FUZZ_TARGETS` is the narrowest safe discovery extension because it lets app modules opt into fuzzing without auto-targeting route handlers, providers, or human checkpoints.
- Benchmark injection can be a Python API for now; CI wiring can call it later without changing merge-blocking behavior.

## Phase 1: Real Gateway Helper Fuzz Target

### Changes

#### 1. Extract Anthropic payload mapper

**File**: `app/proxy/payloads.py`  
**Action**: create

- Add `FUZZ_TARGETS = ("to_anthropic_payload",)`.
- Add `to_anthropic_payload(payload: Mapping[str, Any]) -> dict[str, Any]`.
- Preserve current Anthropic mapping behavior for valid OpenAI-shaped payloads.
- Raise `TypeError` for non-mapping payloads and `ValueError` for payloads missing a usable `model`.

#### 2. Use extracted helper

**File**: `app/proxy/providers/anthropic.py`  
**Action**: modify

- Import `to_anthropic_payload`.
- Remove the static `_to_anthropic_payload` implementation.
- Call `to_anthropic_payload(payload)` from both non-stream and stream paths.

#### 3. Update fuzz chamber discovery and classification

**File**: `governance/governance/steps/fuzz_chamber.py`  
**Action**: modify

- Parse explicit module-level `FUZZ_TARGETS` assignments.
- Add explicit target names even if they are private or otherwise not publicly discoverable.
- Classify `TypeError`/`ValueError` as `rejected`.
- Track `rejections` and `targets` metrics.
- Skip human checkpoint files by path marker.

#### 4. Add tests

**File**: `governance/tests/test_fuzz_benchmark_helpers.py`  
**Action**: create

- Import `fuzz_chamber`.
- Add a test that runs fuzz on `app/proxy/payloads.py`, asserts pass, asserts `functions_tested >= 1`, and asserts no crashes.
- Add a test that includes `app/proxy/interceptor.py` and asserts no interceptor target is executed.

### Verification

#### Automated

- [x] `cd governance && python3 -m pytest tests/test_steps.py tests/test_fuzz_benchmark_helpers.py -q` passes.

#### Manual

- [x] autonomous: verified via `git diff -- app/proxy/interceptor.py --exit-code`.

---

## Phase 2: Benchmark Injection API and Docs

### Changes

#### 1. Add benchmark injection API

**File**: `governance/governance/steps/benchmark_engine.py`  
**Action**: modify

- Add `BenchmarkTarget` dataclass.
- Add `profile_target(...)` and `profile_targets(...)`.
- Let `run(..., targets=None)` merge injected target profiles into metrics under `injected_profiles`.
- Keep default calibration profile behavior unchanged and `passed=True`.

#### 2. Add benchmark injection tests

**File**: `governance/tests/test_fuzz_benchmark_helpers.py`  
**Action**: create

- Import `BenchmarkTarget` and `benchmark_engine`.
- Add a test that injects a linear target, asserts `run(...).passed`, and asserts metrics include the target name.

#### 3. Document per-PR injection

**File**: `governance/README.md`  
**Action**: modify

- Add a "Benchmark target injection" section with a minimal Python snippet.
- State it is informational and currently intended for per-PR/custom checks.

### Verification

#### Automated

- [x] `cd governance && python3 -m pytest tests/test_steps.py tests/test_fuzz_benchmark_helpers.py -q` passes.
- [x] `python3 -m pytest -q` from repository root passes.
- [x] `cd governance && python3 -m governance.cli run --root .. --skip-llm --no-fail-on-error --json-out ../thoughts/qrspi/2026-07-20-gov-fuzz-bench-helpers/governance-report.json` runs and writes a report.

#### Manual

- [x] autonomous: inspected governance report JSON; `fuzz_chamber.metrics.functions_tested == 1`, `crashes == 0`, target is `app/proxy/payloads.py:to_anthropic_payload`, and `benchmark_engine.metrics.profiles` is present.
- [x] autonomous: verified via `git diff -- app/proxy/interceptor.py --exit-code`.

## Stage 6 Worktree / Branch Isolation

- [x] Current implementation branch is `cursor/gov-fuzz-bench-helpers-5e0d`, based on `origin/cursor/qrspi-ledger-land-5e0d`.
- [x] QRSPI artifacts are present on the implementation branch.

## Stage 8 PR Draft

- [x] Write `/tmp/pr-drafts/agent6.md`.
- [x] Write `/workspace/.pr-drafts/agent6.md`.
