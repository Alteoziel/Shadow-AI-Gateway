"""Step 5 — Copyright Filter: rolling-hash plagiarism / verbatim copy detection."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from governance.models import Finding, Severity, StepResult

STEP_ID = "copyright_filter"
STEP_NAME = "Copyright Filter (Anti-Plagiarism)"

# Rabin-Karp parameters
BASE = 256
MOD = 10**9 + 7
WINDOW = 40  # characters per rolling window (normalized)

SIGNATURE_DB = Path(__file__).resolve().parent.parent / "signatures" / "known_snippets.json"


def normalize(text: str) -> str:
    """Strip comments/whitespace noise so formatting clones still match."""
    # Drop Python/JS comments
    text = re.sub(r"#.*", "", text)
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"\s+", "", text).lower()


def _fingerprint(window: str) -> int:
    h = 0
    for ch in window:
        h = (h * BASE + ord(ch)) % MOD
    return h


def rolling_hashes(normalized: str, window: int = WINDOW) -> set[int]:
    """Rabin-Karp rolling hash set over a normalized string."""
    if len(normalized) < window:
        if not normalized:
            return set()
        return {_fingerprint(normalized)}

    hashes: set[int] = set()
    # Initial window
    h = _fingerprint(normalized[:window])
    hashes.add(h)
    power = pow(BASE, window - 1, MOD)

    for i in range(window, len(normalized)):
        left = ord(normalized[i - window])
        right = ord(normalized[i])
        h = (h - left * power) % MOD
        h = (h * BASE + right) % MOD
        hashes.add(h)
    return hashes


def levenshtein(a: str, b: str) -> int:
    """Classic edit-distance for short snippet confirmation."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    # Cap to keep CI bounded
    a, b = a[:400], b[:400]
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def load_signatures() -> list[dict]:
    if not SIGNATURE_DB.exists():
        return []
    return json.loads(SIGNATURE_DB.read_text(encoding="utf-8"))


def sha256_norm(text: str) -> str:
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def scan_source(path: Path, source: str, signatures: list[dict]) -> list[Finding]:
    findings: list[Finding] = []
    norm = normalize(source)
    file_hashes = rolling_hashes(norm)
    file_digest = sha256_norm(source)

    for sig in signatures:
        sig_norm = normalize(sig["content"])
        # Exact normalized match
        if file_digest == hashlib.sha256(sig_norm.encode()).hexdigest():
            findings.append(
                Finding(
                    step=STEP_ID,
                    severity=Severity.CRITICAL,
                    message=f"Exact normalized match against protected snippet `{sig['id']}`",
                    file=str(path),
                    rule_id="COPY001_EXACT",
                    evidence=sig.get("description"),
                    suggestion="Rewrite original logic; do not paste known solutions.",
                )
            )
            continue

        sig_hashes = set(sig.get("hashes") or list(rolling_hashes(sig_norm)))
        if not sig_hashes or not file_hashes:
            continue
        overlap = len(file_hashes & sig_hashes) / len(sig_hashes)
        if overlap >= 0.85:
            # Confirm with Levenshtein on a window of the signature body
            dist = levenshtein(sig_norm[:200], norm[:200])
            ratio = dist / max(len(sig_norm[:200]), 1)
            if ratio <= 0.25:
                findings.append(
                    Finding(
                        step=STEP_ID,
                        severity=Severity.ERROR,
                        message=(
                            f"High similarity ({overlap:.0%} hash overlap) to protected "
                            f"snippet `{sig['id']}` ({sig.get('description', '')})"
                        ),
                        file=str(path),
                        rule_id="COPY002_SIMILAR",
                        evidence=f"levenshtein_ratio={ratio:.2f}",
                        suggestion="Rewrite from first principles; avoid verbatim clones.",
                    )
                )
    return findings


def run(paths: list[Path]) -> StepResult:
    signatures = load_signatures()
    findings: list[Finding] = []
    scanned = 0

    for path in paths:
        if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx", ".js", ".jsx"}:
            continue
        if path.name == "known_snippets.json":
            continue
        scanned += 1
        source = path.read_text(encoding="utf-8", errors="replace")
        findings.extend(scan_source(path, source, signatures))

    blocking = [f for f in findings if f.severity in (Severity.ERROR, Severity.CRITICAL)]
    return StepResult(
        step=STEP_ID,
        name=STEP_NAME,
        passed=len(blocking) == 0,
        findings=findings,
        metrics={
            "files_scanned": scanned,
            "signatures": len(signatures),
            "findings": len(findings),
            "blocking": len(blocking),
        },
    )
