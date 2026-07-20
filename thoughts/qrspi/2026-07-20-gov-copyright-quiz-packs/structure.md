# Structure Outline

## Approach

Implement two small vertical governance slices: one expands Step 5 protected signatures with FastAPI/httpx examples, and one expands Step 6 deterministic quiz generation with Phase 1 provider/streaming/501 comprehension checks.

## Phase 1: Copyright signatures for gateway anti-patterns

This phase grows the protected snippet database and proves at least one new signature blocks a copied FastAPI/httpx anti-pattern.

**Files**: `governance/governance/signatures/known_snippets.json`, `governance/tests/test_steps.py`

**Key changes**:

- Add 5 new JSON signature records with `id`, `description`, and `content`.
- Add `test_copyright_exact_match_fastapi_httpx_antipattern(tmp_path: Path) -> None`.

**Verify**: `cd governance && python -m pytest tests/test_steps.py -k copyright` passes.

---

## Phase 2: Phase 1 comprehension quiz packs

This phase makes deterministic quiz generation teach provider vocabulary/flow, streaming behavior, and 501 checkpoint ownership.

**Files**: `governance/governance/steps/comprehension_gate.py`, `governance/tests/test_steps.py`

**Key changes**:

- Add glossary terms for provider, upstream provider, streaming/SSE, and HTTP 501.
- Add deterministic questions with IDs such as `phase1_provider_selection`, `phase1_streaming_flow`, and `phase1_checkpoint_501`.
- Extend `test_comprehension_generates_quiz` to assert the new questions/categories are generated and preserve the human-owned checkpoint message.

**Verify**: `cd governance && python -m pytest tests/test_steps.py -k comprehension` passes.

---

## Phase 3: QRSPI and PR artifacts

This phase records verification and prepares review drafts without changing runtime gateway code.

**Files**: `thoughts/qrspi/2026-07-20-gov-copyright-quiz-packs/*`, `/tmp/pr-drafts/agent7.md`, `.pr-drafts/agent7.md`

**Key changes**:

- Update `plan.md` checkboxes during implementation.
- Add `worktree.md`, `implement.md`, and `pr.md` stage artifacts.
- Write matching PR draft files.

**Verify**: full governance pytest, governance CLI smoke test, and `git diff -- app/proxy/interceptor.py` show success/empty diff.

## Testing Checkpoints

- After Phase 1, copyright tests pass and the signature count is at least seven total records.
- After Phase 2, deterministic quiz packs include provider, streaming, 501, and human-owned checkpoint questions.
- After Phase 3, artifacts and PR drafts exist, tests pass, branch is pushed, and the interceptor diff is empty.
