# Structure Outline

## Approach

Extract one real Anthropic payload mapper into a top-level pure helper and make fuzz discovery intentionally target it while preserving expected rejection behavior. Add an informational benchmark target API and docs/tests without changing CI blocking semantics.

## Phase 1: Real Gateway Helper Fuzz Target

Extract and use a real payload helper, then update fuzz discovery/classification so Step 3 reaches it and does not flag expected contract rejections as crashes.

**Files**: `app/proxy/payloads.py`, `app/proxy/providers/anthropic.py`, `governance/governance/steps/fuzz_chamber.py`, `governance/tests/test_steps.py`

**Key changes**:

- `to_anthropic_payload(payload: Mapping[str, Any]) -> dict[str, Any]` — new pure gateway helper.
- `FUZZ_TARGETS: tuple[str, ...]` — explicit app helper registry for fuzz.
- `_discover_fuzz_targets(path: Path) -> list[str]` — include explicit targets and public pure helpers.
- Harness status `rejected` — expected contract rejection for invalid fuzz input.

**Verify**: `cd governance && pytest tests/test_steps.py -q` passes and fuzz metrics show at least one function tested for `app/proxy/payloads.py`.

---

## Phase 2: Benchmark Injection API and Docs

Expose a small target object/API for future per-PR benchmark injection while leaving the default benchmark step informational.

**Files**: `governance/governance/steps/benchmark_engine.py`, `governance/tests/test_steps.py`, `governance/README.md`

**Key changes**:

- `BenchmarkTarget(name: str, fn: Callable[[list[int]], object], sizes: Sequence[int], expected: str | None)` — new target descriptor.
- `profile_target(target: BenchmarkTarget) -> dict[str, object]` — profile one injected target.
- `profile_targets(targets: Iterable[BenchmarkTarget]) -> dict[str, dict[str, object]]` — profile many injected targets.
- `run(paths: list[Path] | None = None, targets: Iterable[BenchmarkTarget] | None = None) -> StepResult` — include injected target metrics when provided.

**Verify**: `cd governance && pytest tests/test_steps.py -q` passes and benchmark tests assert injected metrics are present.

---

## Testing Checkpoints

- After Phase 1, `fuzz_chamber.run([root/app/proxy/payloads.py])` passes with `functions_tested >= 1` and no crashes.
- After Phase 2, `benchmark_engine.run(targets=[...])` passes with a named injected profile.
- Final verification: root tests, governance tests, and `ai-guardrail run --root .. --skip-llm --no-fail-on-error --json-out ...` from `governance/`.
