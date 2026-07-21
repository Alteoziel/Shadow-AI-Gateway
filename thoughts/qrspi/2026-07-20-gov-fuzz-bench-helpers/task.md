# Task

Improve governance Step 3 and Step 4 so fuzzing and benchmarking can exercise real gateway helpers instead of only calibration/checkpoint surfaces. The fuzz chamber must target at least one real non-checkpoint pure helper without reporting expected contract rejections as crashes, and benchmark support should expose a documented per-PR injection API while remaining informational.

Scope is limited to governance fuzz/benchmark helper targeting, any small helper extraction needed for a real app target, tests, docs, and PR draft artifacts. `app/proxy/interceptor.py` remains a human checkpoint and must stay untouched.

## Autonomous notes

- Rejected framing: "make the interceptor pass fuzz" because the Ledger marks Checkpoint #1 as blocked on human and requires the function to continue raising until implemented.
- Rejected framing: "benchmark arbitrary changed functions automatically" because the request allows an informational API/docs path and automatic per-PR execution would expand the governance blast radius.
