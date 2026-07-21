from app.scrub.types import ScrubRequest, ScrubResult

SCRUB_LATENCY_BUDGET_MS = 100


async def scrub_prompt(request: ScrubRequest) -> ScrubResult:
    """
    Phase 2 pre-forward scrub pipeline entrypoint.

    Human Checkpoint #2 - see architecture_and_roadmap.md Phase 2.
    """
    # -------------------------------------------------------------------------
    # TODO: Human Hands-On Implementation
    #
    # Implement the core string substitution / regex-NLP scrubbing loop here.
    # The pipeline must inspect prompt text and return sanitized text plus
    # findings before a future integration forwards any provider request.
    #
    # Cheat sheet (why this works):
    # 1. Keep the scrub loop local and deterministic so sensitive text is
    #    handled before any prompt can leave the gateway process.
    # 2. Preserve character spans in findings so later audit logs can explain
    #    what was changed without storing the raw secret again.
    # 3. Measure the whole scrub operation against SCRUB_LATENCY_BUDGET_MS
    #    (sub-100ms); expensive NLP must stay outside the hot path or be cached.
    #
    # Scope: implement redaction decisions and result construction only after
    # the human checkpoint begins. Do NOT wire this into app/proxy/interceptor.py
    # or app/api/v1/chat.py in this scaffold, and do NOT add database writes.
    # -------------------------------------------------------------------------
    raise NotImplementedError(
        "Checkpoint #2 pending: implement scrub_prompt in app/scrub/pipeline.py "
        "with sub-100ms latency before wiring it into request flow."
    )
