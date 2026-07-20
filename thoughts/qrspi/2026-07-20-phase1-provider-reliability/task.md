# Task

Improve Phase 1 provider reliability for the FastAPI gateway by turning missing provider credentials and upstream `httpx` failures into clear gateway HTTP errors. Preserve the human-owned interceptor checkpoint contract, including its `NotImplementedError` / 501 behavior, and either normalize Anthropic streaming to the gateway's OpenAI-style SSE contract or document and test an intentional relay behavior.

Artifact note: this QRSPI run is being executed in a Cursor Cloud environment without an exposed Task/generalPurpose subagent tool, so the stage artifacts preserve the required sequencing and input boundaries directly. Rejected alternate framing: this is not a Checkpoint #1 implementation and must not fill `app/proxy/interceptor.py` or any `TODO: Human Hands-On Implementation`.
