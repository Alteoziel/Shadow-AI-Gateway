import { NextRequest, NextResponse } from "next/server";

/**
 * Ingest/review auth for the governance dashboard.
 *
 * - Production / default: GOVERNANCE_DASHBOARD_SECRET is required.
 * - Local-only escape hatch: set GOVERNANCE_ALLOW_INSECURE_DEV=true
 *   (ignored when NODE_ENV=production).
 */
export function isInsecureDevAllowed(): boolean {
  if (process.env.NODE_ENV === "production") return false;
  return process.env.GOVERNANCE_ALLOW_INSECURE_DEV === "true";
}

export function dashboardSecretConfigured(): boolean {
  return Boolean(process.env.GOVERNANCE_DASHBOARD_SECRET?.trim());
}

export function authorizeIngest(req: NextRequest): boolean {
  const expected = process.env.GOVERNANCE_DASHBOARD_SECRET?.trim();
  if (!expected) {
    return isInsecureDevAllowed();
  }
  return req.headers.get("x-governance-secret") === expected;
}

/** Human actions: approve / reject / merge / submit_quiz */
export function authorizeReviewer(req: NextRequest): boolean {
  const reviewer =
    process.env.GOVERNANCE_REVIEWER_SECRET?.trim() ||
    process.env.GOVERNANCE_DASHBOARD_SECRET?.trim();
  if (!reviewer) {
    return isInsecureDevAllowed();
  }
  const provided =
    req.headers.get("x-governance-reviewer-secret") ||
    req.headers.get("x-governance-secret");
  return provided === reviewer;
}

export function unauthorizedResponse(kind: "ingest" | "reviewer" = "ingest") {
  const hint =
    kind === "ingest"
      ? "Set GOVERNANCE_DASHBOARD_SECRET and send header X-Governance-Secret."
      : "Set GOVERNANCE_DASHBOARD_SECRET (or GOVERNANCE_REVIEWER_SECRET) and send header X-Governance-Reviewer-Secret.";
  return NextResponse.json(
    {
      error: "unauthorized",
      message: hint,
    },
    { status: 401 }
  );
}
