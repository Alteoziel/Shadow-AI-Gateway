/**
 * Shared helpers for dashboard API route authorization (site session + secrets).
 */

import { NextRequest } from "next/server";
import {
  authorizeIngest,
  authorizeReviewer,
  dashboardSecretConfigured,
  isInsecureDevAllowed,
  isProductionLike,
} from "@/lib/auth";
import {
  SITE_AUTH_COOKIE,
  siteGateEnabled,
  sitePassword,
  verifySiteSessionToken,
} from "@/lib/siteAuth";

export async function hasValidSiteSession(req: NextRequest): Promise<boolean> {
  const password = sitePassword();
  if (!password) return false;
  const token = req.cookies.get(SITE_AUTH_COOKIE)?.value;
  return verifySiteSessionToken(token, password);
}

/**
 * Read access for review list/detail: site session OR machine secret.
 * Production: fail closed without site gate / secrets.
 * Local: allow open reads only when no dashboard secret is configured (demo mode).
 */
export async function authorizeReviewRead(req: NextRequest): Promise<boolean> {
  if (authorizeIngest(req) || authorizeReviewer(req)) return true;
  if (await hasValidSiteSession(req)) return true;

  if (!isProductionLike() && !siteGateEnabled()) {
    if (isInsecureDevAllowed()) return true;
    // Dev convenience: no secret configured → open local reads.
    if (!dashboardSecretConfigured()) return true;
  }
  return false;
}

export function siteGateMisconfiguredResponse() {
  return Response.json(
    {
      error: "misconfigured",
      message:
        "Production dashboard requires GOVERNANCE_SITE_PASSWORD (or machine auth headers).",
    },
    { status: 503 }
  );
}
