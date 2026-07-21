# Research Questions

## Context

Focus on the FastAPI gateway entrypoint, request routing, proxy call path, and existing testing conventions. Describe current behavior for request lifecycle, logging, and checkpoint contracts without inferring desired changes.

## Questions

1. How is the FastAPI application assembled, and how do requests reach `/health` and `/v1/chat/completions`?
2. What is the current proxy call flow from the chat endpoint through the interceptor and provider streaming helpers?
3. What logging, request metadata, or observability patterns already exist in the gateway code?
4. What do the existing tests assert for health, proxy routing, and the interceptor contract?
5. What project commands and dependency conventions are used to run gateway tests?
