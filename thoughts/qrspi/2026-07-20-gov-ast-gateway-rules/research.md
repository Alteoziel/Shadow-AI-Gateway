# Research Findings

## Q1: How does the governance pipeline discover, run, and report AST-based checks, and what result contracts do governance steps use?

### Findings

- `run_pipeline()` resolves scannable paths with `collect_paths()` before invoking step modules. It scans explicit `--file` paths, changed files from `git diff --name-only --diff-filter=ACMR`, or the default folders `app`, `governance/governance`, `governance/tests`, and `tests`. (`governance/governance/pipeline.py:18-52`)
- The pipeline runs `ast_guardrail.run(paths)` first, then security, fuzz, benchmark, copyright, and comprehension steps. (`governance/governance/pipeline.py:109-133`)
- Pipeline success is `all(s.passed or s.skipped for s in steps)`, and summary blocking findings count severities whose values are `error` or `critical`. (`governance/governance/pipeline.py:135-151`)
- Governance findings use `Finding(step, severity, message, file, line, rule_id, evidence, suggestion)`. (`governance/governance/models.py:18-26`)
- Governance steps return `StepResult(step, name, passed, findings, metrics, skipped, skip_reason)`. (`governance/governance/models.py:29-36`)
- `PipelineReport.error_count()` treats `Severity.ERROR` and `Severity.CRITICAL` as errors. (`governance/governance/models.py:46-52`)

## Q2: What rules does the existing AST guardrail enforce today, and how does it parse Python source files and produce violations?

### Findings

- The AST step is identified by `STEP_ID = "ast_guardrail"` and `STEP_NAME = "AST Guardrail (Code Structure Analysis)"`. (`governance/governance/steps/ast_guardrail.py:10-11`)
- `FORBIDDEN_CALLS` includes bare `eval`, `exec`, `compile`, and `__import__`. (`governance/governance/steps/ast_guardrail.py:13-18`)
- `_StructureVisitor` tracks loop depth across `For`, `While`, and `AsyncFor`; depths above `MAX_NESTED_LOOPS = 2` add an `AST001_NESTED_LOOPS` error. (`governance/governance/steps/ast_guardrail.py:20-60`)
- `visit_Call()` flags only bare-name forbidden calls, not attributes such as `re.compile`, and emits `AST002_FORBIDDEN_CALL` as critical. (`governance/governance/steps/ast_guardrail.py:66-82`)
- Function complexity counts `If`, `For`, `While`, `ExceptHandler`, and `With` nodes from `ast.walk()`; more than 15 branch points adds `AST003_COMPLEXITY` as warning. (`governance/governance/steps/ast_guardrail.py:84-112`)
- `analyze_file()` reads UTF-8 source, returns an `AST000_SYNTAX` error on syntax errors, otherwise visits the parsed tree. (`governance/governance/steps/ast_guardrail.py:121-138`)
- `run()` filters input paths to existing `.py` files, accumulates findings from `analyze_file()`, and fails only when findings are `ERROR` or `CRITICAL`. (`governance/governance/steps/ast_guardrail.py:142-159`)

## Q3: What patterns do governance tests use for step-level assertions, pipeline assertions, fixtures, and expected statuses?

### Findings

- Existing tests live in `governance/tests/test_steps.py` and import step modules directly. (`governance/tests/test_steps.py:1-12`)
- AST tests create temporary Python files with `tmp_path`, call `ast_guardrail.run([src])`, assert `result.passed`, and check `rule_id` values in `result.findings`. (`governance/tests/test_steps.py:15-48`)
- Security and copyright tests follow the same pattern: temporary file, step `run()`, pass/fail assertion, and rule-id assertion. (`governance/tests/test_steps.py:51-81`)
- Comprehension tests call `comprehension_gate.run(..., skip_llm=True)` and assert metrics content rather than only pass/fail. (`governance/tests/test_steps.py:84-101`)
- No pipeline-level tests appear in the current `governance/tests/test_steps.py`; tests are step-level and utility-level. (`governance/tests/test_steps.py:1-157`)

## Q4: Where do gateway chat requests flow through route, interceptor, streaming, and provider modules, and what call ordering is visible in the current source?

### Findings

- The chat route imports `intercept_outbound_request`, `AnthropicProvider`, `BaseLLMProvider`, `OpenAIProvider`, and `relay_sse_stream`. (`app/api/v1/chat.py:7-13`)
- `chat_completions()` builds `raw_body` and request `headers`, then awaits `intercept_outbound_request(...)` inside a `try` block. (`app/api/v1/chat.py:81-96`)
- Provider resolution and adapter construction occur after the interceptor call: `_resolve_provider(request_body)` and `_get_provider_adapter(provider_name)` are on later lines. (`app/api/v1/chat.py:99-101`)
- Streaming requests call `provider.chat_completion_stream(payload)` and then `relay_sse_stream(upstream, on_complete=provider.aclose)`. (`app/api/v1/chat.py:103-111`)
- Non-streaming requests call `provider.chat_completion(payload)` and close the provider in `finally`. (`app/api/v1/chat.py:113-116`)
- `intercept_outbound_request()` is an async function in `app/proxy/interceptor.py`; it contains a human checkpoint comment and raises `NotImplementedError`. (`app/proxy/interceptor.py:4-39`)
- `relay_sse_stream()` accepts an `httpx.Response`, asynchronously iterates `upstream.aiter_bytes()`, closes the upstream response, and optionally calls `on_complete`. (`app/proxy/streaming.py:6-37`)
- `OpenAIProvider` and `AnthropicProvider` both instantiate `httpx.AsyncClient` in `__init__`, await `_client.post()` for non-streaming calls, and use `_client.send(..., stream=True)` for streams. (`app/proxy/providers/openai.py:14-49`, `app/proxy/providers/anthropic.py:15-128`)

## Q5: Where do `httpx` and `requests` appear under `app/` and `governance/`, and are those appearances synchronous clients, async clients, imports, or test strings?

### Findings

- Under `app/`, `httpx` appears in type annotations and imports in `app/proxy/streaming.py` and `app/proxy/providers/base.py`. (`app/proxy/streaming.py:3-41`, `app/proxy/providers/base.py:1-23`)
- Under `app/`, `OpenAIProvider` imports `httpx` and creates `httpx.AsyncClient`; its HTTP calls are awaited on the async client. (`app/proxy/providers/openai.py:1-49`)
- Under `app/`, `AnthropicProvider` imports `httpx` and creates `httpx.AsyncClient`; its HTTP calls are awaited on the async client. (`app/proxy/providers/anthropic.py:1-128`)
- Under `app/`, the string `httpx` also appears in a comment in the chat route and in an interceptor comment about `async def`; those are not client construction calls. (`app/api/v1/chat.py:103-105`, `app/proxy/interceptor.py:24-29`)
- No `requests` usage appears under `app/` in the searched Python files. (`rg "\b(httpx|requests)\b" --glob "*.py"`)
- Under `governance/`, `security_auditor.py`, `comprehension_gate.py`, and `reporters/github.py` import `httpx` and use synchronous `httpx.Client(...)` for governance-side API calls. (`governance/governance/steps/security_auditor.py:8-9`, `governance/governance/steps/security_auditor.py:112-119`, `governance/governance/steps/comprehension_gate.py:595-602`, `governance/governance/reporters/github.py:56-126`)
- `security_auditor.py` has a deterministic regex that matches `httpx.get`, `httpx.post`, `httpx.request`, `requests.get`, `requests.post`, and `urllib.request`. (`governance/governance/steps/security_auditor.py:45-51`)

## Q6: How is the `ai-guardrail` CLI configured and invoked locally or in CI, including the behavior of `--skip-llm`?

### Findings

- The governance package exposes `ai-guardrail = "governance.cli:app"` as a project script. (`governance/pyproject.toml:20-21`)
- The `run` command accepts `--root`, `--file`, `--changed-only`, `--base-ref`, `--skip-fuzz`, `--skip-llm`, output, PR comment, dashboard, and failure-control options. (`governance/governance/cli.py:38-71`)
- The CLI passes `skip_llm` into `run_pipeline()`. (`governance/governance/cli.py:73-84`)
- The pipeline passes `diff_text=None if skip_llm else diff_text` to `security_auditor.run()` and passes `skip_llm` to `comprehension_gate.run()`. (`governance/governance/pipeline.py:109-133`)
- The CLI raises exit code 1 when `--fail-on-error` remains true and the report does not pass. (`governance/governance/cli.py:139-140`)
- The GitHub workflow installs the governance engine from `governance/`, runs `pytest -q`, then runs `ai-guardrail` with `run --root ..`, report outputs, dashboard posting, and PR flags for pull requests. (`.github/workflows/ai-guardrail.yml:32-72`)
- Local README examples show `ai-guardrail run --root .`, `ai-guardrail quiz --root . --skip-llm`, file-specific runs, and changed-only runs. (`governance/README.md:26-35`)

## Cross-Cutting Observations

- AST findings, security findings, and copyright findings all use `rule_id` strings as stable test targets. (`governance/tests/test_steps.py:15-81`)
- The app route currently shows interceptor-before-provider ordering in source order. (`app/api/v1/chat.py:89-101`)
- App provider modules use async HTTP client construction, while governance-side integrations use synchronous clients. (`app/proxy/providers/openai.py:14-49`, `app/proxy/providers/anthropic.py:15-128`, `governance/governance/steps/security_auditor.py:112-119`)

## Open Areas

- Research did not inspect generated CI logs or external PR settings.
- Research did not execute tests; this stage records source facts only.
