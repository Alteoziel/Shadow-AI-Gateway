# Implementation Plan

## Overview

Add a gateway-focused pytest matrix and independent CI workflow that validate Phase 1 behavior around Checkpoint #1 without implementing `app/proxy/interceptor.py`.

## Autonomous Assumptions

- `respx>=0.23.1` is acceptable as a dev dependency because provider adapters use `httpx` and `0.23.1` is the latest available version reported by `python3 -m pip index versions respx`.
- Direct tests of `_resolve_provider` and `_build_upstream_payload` are acceptable because they are route-local Phase 1 contract helpers.
- Manual workflow validation is converted to local pytest plus static inspection because GitHub Actions cannot run before push in this environment.

## Phase 1: Gateway Behavior Test Matrix

### Changes

#### 1. Root dev dependency

**File**: `pyproject.toml`  
**Action**: modify

- Add `respx>=0.23.1` under `[project.optional-dependencies].dev`.

#### 2. Route helper tests

**File**: `tests/test_gateway_payloads.py`  
**Action**: create

- Test `_resolve_provider` with explicit request provider.
- Test `_resolve_provider` with `DEFAULT_PROVIDER=anthropic` and no request provider.
- Test `_build_upstream_payload`:
  - `extra_body` can add non-protected keys.
  - `extra_body` cannot override `model`, `messages`, or `stream`.
  - normalized interceptor output wins for `model` and `messages`.
  - request `stream` wins for `stream`.
  - optional request fields are preserved.

#### 3. Provider adapter tests

**File**: `tests/test_provider_adapters.py`  
**Action**: create

- Test `AnthropicProvider._to_anthropic_payload` maps system messages to `system`, user/assistant messages to `messages`, stop string to `stop_sequences`, default `max_tokens`, and skips unsupported roles.
- Test `AnthropicProvider._to_openai_shape` converts text blocks and usage totals.
- Use `respx` to test OpenAI non-streaming POST URL, auth header, request JSON, and returned JSON.
- Use `respx` to test Anthropic non-streaming POST mapped JSON and returned OpenAI-compatible shape.
- Use `respx` to test OpenAI and Anthropic streaming requests send `"stream": true`.

#### 4. Streaming relay tests

**File**: `tests/test_streaming_relay.py`  
**Action**: create

- Build an `httpx.Response` with streaming bytes.
- Call `relay_sse_stream`.
- Assert body bytes are yielded, hop-by-hop headers are filtered, status/media type are preserved, upstream is closed, and `on_complete` is awaited.

#### 5. Unlock-path routing test expansion

**File**: `tests/test_proxy_provider_selection.py`  
**Action**: create

- Add a mocked interceptor/provider test showing request-level `provider="anthropic"` selects `AnthropicProvider` after the checkpoint unlocks.

### Verification

#### Automated

- [x] `python3 -m pytest tests -q` passes in `/workspace` (`34 passed`, includes unrelated dirty tests present in the worktree).
- [x] `python3 -m pytest tests -q` passes in clean verification worktree `/tmp/gateway-ci-verify` with only this package copied over (`16 passed`).
- [x] `git diff -- app/proxy/interceptor.py tests/test_interceptor_contract.py` shows no changes in clean verification worktree.

#### Manual

- [x] autonomous: verified via `rg -n 'TODO: Human Hands-On Implementation|raise NotImplementedError' app/proxy/interceptor.py` in clean verification worktree.

---

## Phase 2: Gateway CI Workflow

### Changes

#### 1. App pytest workflow

**File**: `.github/workflows/gateway-ci.yml`  
**Action**: create

- Trigger on pull requests to `main` and `workflow_dispatch`.
- Checkout, set up Python 3.12, install root project with `pip install -e ".[dev]"`, then run `python -m pytest tests -q`.
- Do not modify `.github/workflows/ai-guardrail.yml`.

### Verification

#### Automated

- [x] `python3 -m pytest tests -q` passes after workflow creation in `/workspace` and clean verification worktree.
- [x] `git diff -- .github/workflows/ai-guardrail.yml` shows no changes in clean verification worktree.

#### Manual

- [x] autonomous: inspected `.github/workflows/gateway-ci.yml`; it runs from the repository root and targets `tests`.
