# Research Questions

## Context

Focus on the FastAPI gateway service, its route-level request handling, provider adapters, streaming utilities, existing test suite, and CI layout. Describe current behavior, boundaries, and conventions only.

## Questions

1. How does the chat completions route currently sequence request validation, interception, provider selection, payload construction, and response handling?
2. What provider adapter behavior exists for OpenAI and Anthropic, including request payload transformation, headers, non-streaming calls, streaming calls, and response shape conversion?
3. How does the gateway relay streaming upstream responses, and what lifecycle or cleanup behavior is currently encoded?
4. What tests currently exercise health, checkpoint behavior, routing, and the post-checkpoint unlock path?
5. What project dependency and CI conventions currently exist for app tests versus governance tests?
