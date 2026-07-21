# Research Questions

## Context

Focus on the FastAPI chat completion request path, provider adapter abstractions, streaming helpers, configuration loading, and tests around proxy routing and the interceptor contract. Describe the current behavior and existing patterns without proposing changes.

## Questions

1. How does `POST /v1/chat/completions` flow from request validation through interceptor invocation, provider selection, and streaming or non-streaming response generation?
2. How do the OpenAI and Anthropic provider adapters currently build upstream requests, consume `httpx` responses, and surface errors?
3. What configuration patterns exist for provider API keys and default provider selection, including validation behavior for missing or empty environment values?
4. How is streaming currently represented by the gateway, especially for OpenAI-compatible chunks and Anthropic chunks?
5. What test coverage already exists for provider routing, streaming, error paths, and the human-owned interceptor contract?
