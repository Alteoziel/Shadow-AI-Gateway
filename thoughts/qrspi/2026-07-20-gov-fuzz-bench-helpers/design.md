# Design Discussion

## Current State

- Fuzz discovery only sees public top-level synchronous functions and treats all non-`TypeError` exceptions as crashes, so it misses private/class gateway helpers and can flag expected helper contract rejection as a crash. See `research.md` Q1.
- Gateway payload transformation exists in `_build_upstream_payload` and `AnthropicProvider._to_anthropic_payload`; the active interceptor raises `NotImplementedError` by design. See `research.md` Q2.
- Benchmarking is a self-calibrating informational step with a reusable estimator but no target injection object/API. See `research.md` Q3.
- Tests cover governance basics and the interceptor contract, but not fuzzing a real gateway helper or benchmark injection. See `research.md` Q4.
- The Ledger explicitly asks for real gateway helper fuzz targets and per-PR benchmark injection while preserving the human-owned interceptor checkpoint. See `research.md` Q5.

## Desired End State

- Step 3 discovers and runs at least one real, non-checkpoint gateway pure helper during normal app scans.
- Expected helper input-contract rejections are classified as non-crash results so fuzz does not block on false positives.
- Step 4 exposes a small documented API for injecting per-PR benchmark targets while continuing to pass informationally.
- Tests prove fuzz reaches a gateway helper, avoids the interceptor, and benchmark injection returns metrics.
- `app/proxy/interceptor.py` is untouched.

## Patterns to Follow

- Keep Step 3 subprocess isolation and JSON result flow from `fuzz_chamber.py`.
- Keep Step 4 `passed=True` informational behavior from `benchmark_engine.py`.
- Preserve existing provider route contracts and tests that assert the interceptor still raises.
- Prefer a small helper extraction for Anthropic payload mapping over broad AST support for class methods, because the extracted function becomes a real app code path and a simple fuzz target.

## Autonomous Decisions

1. **Which helper to target?** Choose Anthropic payload mapping by extracting it to a top-level pure helper. It is real gateway logic, already invoked for stream and non-stream requests, and can be fuzzed with one boundary argument.
2. **How should invalid boundary inputs be classified?** Treat `TypeError` and `ValueError` as `rejected` rather than crashes. These represent input-contract rejection for pure helpers; unexpected exceptions remain crashes.
3. **Should fuzz discover all private helpers?** No. Use explicit module-level target naming (`FUZZ_TARGETS`) plus normal public discovery. This avoids accidentally targeting checkpoint code or side-effectful internals.
4. **How should benchmark per-PR injection work?** Add a `BenchmarkTarget` API consumed by `profile_targets(...)` / `run(..., targets=...)`. This is easy for tests and future CI wiring without making automatic discovery block merges.
5. **Should the interceptor be modified or made fuzz-passable?** No. The Ledger forbids completing or softening the human checkpoint, and the task explicitly says not to require it to pass fuzz.

## Design Decisions

1. **Extract `to_anthropic_payload`**: Move the static Anthropic mapper into `app/proxy/payloads.py` and have `AnthropicProvider` call it.
2. **Explicit fuzz target registry**: Let app helper modules declare `FUZZ_TARGETS = ("to_anthropic_payload",)`, and have fuzz discovery include those names even if future naming conventions change.
3. **Contract rejection classification**: Update the harness to record `TypeError`/`ValueError` as `rejected`, keep crashes for unexpected exceptions, and expose a `rejections` metric.
4. **Benchmark injection API**: Add `BenchmarkTarget`, `profile_target`, and `profile_targets`; keep default calibration profiles unchanged.
5. **Focused tests and docs**: Add tests for gateway helper fuzzing and benchmark injection, plus README docs for per-PR injection.

## What We're NOT Doing

- Not implementing `intercept_outbound_request`.
- Not fuzzing provider network methods or route handlers.
- Not auto-discovering arbitrary benchmark functions from changed files.
- Not making benchmark findings block merge.

## Open Risks

- Fuzzing app modules with imports depends on the local Python environment having app dependencies installed; verification will run after checking setup status.
- Boundary cases may all be rejected for strict helper contracts; the success criterion is no crashes and evidence that a real helper was executed.
