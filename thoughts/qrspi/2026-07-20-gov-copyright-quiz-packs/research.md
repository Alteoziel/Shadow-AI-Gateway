# Research Findings

## Q1: How does the copyright filter load, normalize, and compare known snippets, and how are its existing tests structured?

### Findings

- `governance/governance/steps/copyright_filter.py:20` sets `SIGNATURE_DB` to `governance/governance/signatures/known_snippets.json`.
- `governance/governance/steps/copyright_filter.py:23-29` normalizes source by removing Python/JS comments, block comments, whitespace, and lowercasing.
- `governance/governance/steps/copyright_filter.py:80-83` loads the signature JSON as a list of dictionaries.
- `governance/governance/steps/copyright_filter.py:91-136` compares file source against each signature using exact normalized digest match first, then rolling-hash overlap plus Levenshtein confirmation.
- `governance/governance/steps/copyright_filter.py:140-160` scans Python/TypeScript/JavaScript files, skips `known_snippets.json` itself, and fails only on error/critical copyright findings.
- `governance/tests/test_steps.py:68-81` creates a temporary source file containing the known `leetcode_two_sum_classic` snippet and asserts the copyright step fails with `COPY001_EXACT` or `COPY002_SIMILAR`.

## Q2: How does the comprehension gate build deterministic study guides and quiz questions, including category labels, manual task detection, and pass threshold metadata?

### Findings

- `governance/governance/steps/comprehension_gate.py:21-23` defines `PASS_THRESHOLD = 0.8`.
- `governance/governance/steps/comprehension_gate.py:27-84` defines project glossary entries for core beginner vocabulary.
- `governance/governance/steps/comprehension_gate.py:87-95` maps quiz categories to readable labels.
- `governance/governance/steps/comprehension_gate.py:146-215` detects manual tasks from changed paths, symbols, TODO markers, `NotImplementedError`, `.env`/config files, governance paths, and dashboard paths.
- `governance/governance/steps/comprehension_gate.py:219-318` builds the deterministic pack with study guide metadata and calls `_make_questions`.
- `governance/governance/steps/comprehension_gate.py:340-549` creates deterministic multiple-choice questions covering vocabulary, bigger picture, functions, flow, dependencies, manual tasks, and security.
- `governance/governance/steps/comprehension_gate.py:676-724` returns a passing Step 6 result when generation succeeds and stores the pack in `metrics["comprehension"]`.

## Q3: What Phase 1 proxy concepts already exist in the application code for provider selection, streaming responses, and the HTTP 501 checkpoint state?

### Findings

- `app/api/v1/chat.py:19-23` defines the 501 detail for pending Checkpoint #1 and states that a human must complete `app/proxy/interceptor.py`.
- `app/api/v1/chat.py:26-28` resolves provider selection from the request provider or default settings.
- `app/api/v1/chat.py:31-37` maps provider names to OpenAI or Anthropic adapters and rejects unsupported providers with HTTP 400.
- `app/api/v1/chat.py:88-97` calls `intercept_outbound_request` before resolving/using the provider and converts `NotImplementedError` into HTTP 501.
- `app/api/v1/chat.py:103-111` uses `chat_completion_stream` plus `relay_sse_stream` when `request_body.stream` is true.
- `app/proxy/streaming.py:6-36` relays upstream SSE/chunked response bytes through `StreamingResponse` and strips hop-by-hop/content-length headers.

## Q4: What governance test conventions exist for adding generation coverage without relying on optional LLM calls?

### Findings

- `governance/tests/test_steps.py:83-102` calls `comprehension_gate.run(..., skip_llm=True)` against a temporary Python file and asserts generated pack metadata, question count, glossary, and manual task content.
- `governance/tests/test_steps.py:104-159` tests grading with a small in-memory pack instead of invoking CLI or external services.
- `governance/pyproject.toml:30-32` configures pytest to discover tests in `governance/tests`.

## Q5: What repository rules currently protect `app/proxy/interceptor.py` as a human-owned checkpoint?

### Findings

- `architecture_and_roadmap.md:1-12` says the Ledger is law, QRSPI is mandatory, and QRSPI autonomy does not authorize agents to complete Human-in-the-Loop checkpoints.
- `architecture_and_roadmap.md:116-118` states the default cycle ends with human-filled product checkpoints and repeats that QRSPI autonomy does not override them.
- `architecture_and_roadmap.md:257-262` says agents may scaffold, document, validate contracts, and add tests around checkpoints, but Checkpoint #1 remains `blocked_on_human` until the human fills the implementation.
- `app/proxy/interceptor.py:13-18` documents Human Checkpoint #1 and contains the `TODO: Human Hands-On Implementation` marker.
- `app/proxy/interceptor.py:37-40` still raises `NotImplementedError` for the checkpoint.

## Cross-Cutting Observations

- The governance code favors deterministic generation and local pytest coverage before optional LLM enrichment.
- The quiz generator already teaches Checkpoint #1 as human-owned in manual task explanations; new Phase 1 questions can reinforce that rather than replace it.
- Copyright signatures are plain JSON content snippets; no code change is required for the database to grow.

## Open Areas

- No generated quiz pack artifact format beyond the in-memory metrics was found in the current code. Tests can assert generated question IDs/categories directly.
