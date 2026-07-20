# Research Findings

## Stage Isolation

- Research input used: `questions.md` only.
- `task.md` was not read for this stage; implementation intent is intentionally absent from the research questions.

## Q1: How is the gateway package organized today, and what import/export patterns exist for small focused subpackages?

### Findings

- The Python package is discovered from the repository root with setuptools including `app*`, so new `app` subpackages are importable when they include normal Python modules. `pyproject.toml:24-27`
- The FastAPI app is assembled in `create_app()`, which includes the health router and chat router directly. `app/main.py:31-40`
- The proxy package exposes its public checkpoint function through `app/proxy/__init__.py`, keeping the subpackage export narrow. `app/proxy/__init__.py:1-5`
- Existing providers follow small module boundaries: an abstract base interface lives in `app/proxy/providers/base.py`, and provider adapters are imported by the chat route. `app/proxy/providers/base.py:1-27`, `app/api/v1/chat.py:9-12`

## Q2: What patterns do existing human-owned checkpoint stubs use for TODO text, cheat sheets, exceptions, and tests?

### Findings

- `intercept_outbound_request(...)` is async, keyword-only, and currently returns `dict[str, Any]` once implemented. `app/proxy/interceptor.py:5-10`
- The interceptor docstring identifies the pre-flight purpose and points reviewers to the Ledger checkpoint section. `app/proxy/interceptor.py:11-16`
- The checkpoint body includes a fenced comment banner, `TODO: Human Hands-On Implementation`, a 3-bullet cheat sheet, scope rules, and a final `NotImplementedError`. `app/proxy/interceptor.py:18-40`
- Existing tests assert the checkpoint function is callable, async, and raises `NotImplementedError` while the human checkpoint remains incomplete. `tests/test_interceptor_contract.py:10-19`

## Q3: How do current tests assert placeholder behavior and route wiring without invoking upstream providers?

### Findings

- The chat routing test asserts the live route returns 501 while Checkpoint #1 is not implemented, and checks the response detail mentions the checkpoint and function name. `tests/test_proxy_routing.py:16-23`
- The provider forwarding test patches `app.api.v1.chat.intercept_outbound_request` with an `AsyncMock` and patches `OpenAIProvider`, proving route behavior without calling a real provider. `tests/test_proxy_routing.py:25-64`
- The interceptor contract test parses `app/api/v1/chat.py` with `ast` and confirms `intercept_outbound_request` appears before provider-related calls. `tests/test_interceptor_contract.py:21-44`

## Q4: Where does the Ledger track phase checkpoint file paths and statuses, and what exact fields must remain consistent?

### Findings

- The Ledger top banner says current phase is Phase 1 and Checkpoint #1 is `blocked_on_human` at `app/proxy/interceptor.py`. `architecture_and_roadmap.md:8-12`
- Phase 1 table records status `in_progress`, checkpoint status `blocked_on_human`, checkpoint file `app/proxy/interceptor.py`, and human ownership. `architecture_and_roadmap.md:126-133`
- Phase 2 table records status `not_started`, checkpoint status `not_started`, checkpoint file `TBD - core string substitution / regex-NLP scrubbing loop`, and human ownership. `architecture_and_roadmap.md:165-172`
- The progression audit table repeats checkpoint file, owner, phase status, and checkpoint status for all phases. `architecture_and_roadmap.md:216-223`
- The non-negotiable guardrails require sub-100ms scrub budget validation from Phase 2 onward and prohibit agents from auto-completing human checkpoint blocks. `architecture_and_roadmap.md:350-359`
- The resume defense map still lists the Phase 2 human-owned artifact as a TBD scrub loop path. `architecture_and_roadmap.md:370-376`

## Q5: What project commands and dependencies are available for focused automated verification?

### Findings

- The project targets Python 3.12 and has FastAPI, Uvicorn, httpx, and pydantic-settings as runtime dependencies. `pyproject.toml:1-12`
- Dev dependencies include `pytest`, `pytest-asyncio`, and `httpx`. `pyproject.toml:14-19`
- Pytest is configured with `asyncio_mode = "auto"` and `testpaths = ["tests"]`. `pyproject.toml:29-31`
- The README documents local setup with `pip install -e ".[dev]"` and test execution with `pytest`. `README.md:50-59`, `README.md:99-103`

## Cross-Cutting Observations

- Human-owned checkpoint placeholders are treated as intentional product states and covered by tests rather than skipped.
- Current route tests use mocking and source inspection to verify boundaries without real upstream calls.
- Ledger updates must touch both the phase table and the progression audit table when checkpoint paths change.

## Open Areas

- No existing `app/scrub/` package or scrub-specific tests were found in the gateway package.
