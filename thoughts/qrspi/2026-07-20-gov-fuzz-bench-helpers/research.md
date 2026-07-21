# Research Findings

## Q1: How does the fuzz chamber currently discover Python functions, invoke them, and classify boundary-input outcomes?

### Findings

- `governance/governance/steps/fuzz_chamber.py:16-26` defines deterministic boundary cases including `None`, `[]`, scalars, a proto-shaped dict, and a large string.
- `governance/governance/steps/fuzz_chamber.py:28-62` writes a subprocess harness that `exec`s one target file, looks up a function by name from the module namespace, calls it once per boundary case, marks `TypeError` separately, and marks every other exception as `crash`.
- `governance/governance/steps/fuzz_chamber.py:65-78` discovers only top-level `ast.FunctionDef` nodes that do not start with `_`, have one or two positional args, and have no decorators.
- `governance/governance/steps/fuzz_chamber.py:111-177` skips tests, governance step modules, CLI, pipeline, and reporters; it increments `functions_tested` per discovered job and fails the step when any crash is recorded.

## Q2: Which real gateway helper functions transform chat payloads before provider calls, and where are they defined or invoked?

### Findings

- `app/api/v1/chat.py:40-78` defines `_build_upstream_payload`, a pure helper that merges request fields, additive `extra_body`, normalized metadata, and protected `model/messages/stream` fields.
- `app/api/v1/chat.py:89-101` invokes `intercept_outbound_request` before resolving the provider and then builds the upstream payload with `_build_upstream_payload`.
- `app/proxy/providers/anthropic.py:27-68` defines `AnthropicProvider._to_anthropic_payload`, a static helper that maps OpenAI-shaped gateway messages into Anthropic Messages API fields.
- `app/proxy/providers/anthropic.py:70-96` invokes `_to_anthropic_payload` for both non-streaming and streaming Anthropic requests.
- `app/proxy/interceptor.py:4-40` defines `intercept_outbound_request` as the active human checkpoint and raises `NotImplementedError`.

## Q3: How does the benchmark engine currently profile functions, classify complexity, and expose metrics to the pipeline?

### Findings

- `governance/governance/steps/benchmark_engine.py:14-26` times a callable over list sizes by passing `list(range(n))` and keeping the best repeat time.
- `governance/governance/steps/benchmark_engine.py:29-56` classifies growth with a log-log slope between the two largest stable points.
- `governance/governance/steps/benchmark_engine.py:59-99` profiles three internal calibration functions: linear scan, hash join, and capped quadratic scan.
- `governance/governance/steps/benchmark_engine.py:102-150` ignores `paths`, always returns `passed=True`, and exposes profile metrics for dashboard plotting.
- `governance/governance/pipeline.py:124-127` always runs benchmark after fuzz and before copyright.

## Q4: What tests currently cover the governance steps, gateway provider routing, and human checkpoint contract?

### Findings

- `governance/tests/test_steps.py:16-48` covers AST guardrail nested-loop, eval, and clean-file behavior.
- `governance/tests/test_steps.py:60-65` covers the benchmark estimator with synthetic linear timing data.
- `governance/tests/test_steps.py:84-101` verifies comprehension quiz generation from a small interceptor-like source.
- `tests/test_proxy_routing.py:16-22` asserts chat completions return 501 while the interceptor checkpoint is not implemented.
- `tests/test_proxy_routing.py:25-64` patches the interceptor and provider to document the provider-forwarding unlock path.
- `tests/test_interceptor_contract.py:10-19` asserts the interceptor exists, is async, and currently raises `NotImplementedError`.

## Q5: How do docs and the Ledger describe the relationship between fuzzing, benchmarking, per-PR extension work, and the human-owned interceptor checkpoint?

### Findings

- `architecture_and_roadmap.md:31-39` lists fuzz as blocking on crashes and benchmark as informational.
- `architecture_and_roadmap.md:139-141` identifies `intercept_outbound_request` as the human pre-flight checkpoint.
- `architecture_and_roadmap.md:257-264` forbids agents from completing `TODO: Human Hands-On Implementation` blocks and names `app/proxy/interceptor.py` as blocked on human.
- `architecture_and_roadmap.md:443-445` lists future setup work to target real gateway helpers for fuzzing and wire per-PR function injection for benchmarking.
- `governance/README.md:1-44` describes governance install, local run commands, and Step 3/4 roles but does not document per-PR benchmark injection.

## Cross-Cutting Observations

- The fuzz chamber currently misses private helpers and class static methods, so it does not reach the gateway payload mappers even when scanning `app/`.
- The active interceptor checkpoint is not currently discovered because it is an `async def`, but broader discovery must explicitly keep checkpoint files out of fuzz targets.
- The benchmark engine already has a reusable estimator but no public target wrapper for callers that want to inject PR-specific functions.

## Open Areas

- No existing test exercises fuzzing against a real `app/` helper.
- No existing test or doc demonstrates benchmark target injection.
