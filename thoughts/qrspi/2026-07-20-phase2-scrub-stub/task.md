# Task

Prepare Phase 2 Walk scaffolding for the local data-scrubbing checkpoint without implementing any real scrub logic. Add a human-owned `app/scrub/` pipeline entrypoint with interfaces, a latency-budget test harness stub, Ledger checkpoint path updates, and PR draft artifacts while keeping scrub code unwired from the Phase 1 interceptor and chat route.

## Scope Boundaries

- Do not wire scrub behavior into `app/proxy/interceptor.py` or `app/api/v1/chat.py`.
- Do not implement regex, NLP, tokenization, redaction, or provider mutation logic.
- Do not implement or modify `app/proxy/interceptor.py`.

## Rejected Alternate Framings

- Framing research as "how should we build the scrubber" was rejected because Research must stay neutral and facts-only.
- Treating this as a Phase 2 status transition was rejected; this is checkpoint prep scaffolding only.
