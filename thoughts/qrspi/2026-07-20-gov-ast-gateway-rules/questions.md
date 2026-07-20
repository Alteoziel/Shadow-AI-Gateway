# Research Questions

## Context

Focus on the repository's governance pipeline, AST-based rule implementation, existing governance tests, and the request flow through the gateway's chat route and provider modules. Describe current file organization, rule contracts, and test patterns without evaluating or proposing changes.

## Questions

1. How does the governance pipeline discover, run, and report AST-based checks, and what result contracts do governance steps use?
2. What rules does the existing AST guardrail enforce today, and how does it parse Python source files and produce violations?
3. What patterns do governance tests use for step-level assertions, pipeline assertions, fixtures, and expected statuses?
4. Where do gateway chat requests flow through route, interceptor, streaming, and provider modules, and what call ordering is visible in the current source?
5. Where do `httpx` and `requests` appear under `app/` and `governance/`, and are those appearances synchronous clients, async clients, imports, or test strings?
6. How is the `ai-guardrail` CLI configured and invoked locally or in CI, including the behavior of `--skip-llm`?
