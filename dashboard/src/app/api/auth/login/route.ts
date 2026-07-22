import { NextRequest, NextResponse } from "next/server";
import {
  SITE_AUTH_COOKIE,
  mintSiteSessionToken,
  passwordsMatch,
  siteGateEnabled,
  sitePassword,
  siteSessionCookieOptions,
} from "@/lib/siteAuth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Simple per-IP sliding window for login brute-force protection. */
const LOGIN_WINDOW_MS = 60_000;
const LOGIN_MAX_ATTEMPTS = 5;
const loginBuckets = new Map<string, number[]>();

function clientIp(req: NextRequest): string {
  const forwarded = req.headers.get("x-forwarded-for");
  if (forwarded) return forwarded.split(",")[0]?.trim() || "unknown";
  return req.headers.get("x-real-ip")?.trim() || "unknown";
}

function consumeLoginAttempt(ip: string): boolean {
  const now = Date.now();
  const cutoff = now - LOGIN_WINDOW_MS;
  const prev = (loginBuckets.get(ip) || []).filter((t) => t >= cutoff);
  if (prev.length >= LOGIN_MAX_ATTEMPTS) {
    loginBuckets.set(ip, prev);
    return false;
  }
  prev.push(now);
  loginBuckets.set(ip, prev);
  // Bound map growth
  if (loginBuckets.size > 10_000) {
    for (const [key, stamps] of loginBuckets) {
      const kept = stamps.filter((t) => t >= cutoff);
      if (!kept.length) loginBuckets.delete(key);
      else loginBuckets.set(key, kept);
    }
  }
  return true;
}

export async function POST(req: NextRequest) {
  if (!siteGateEnabled()) {
    return NextResponse.json(
      {
        error: "site_gate_disabled",
        message:
          "GOVERNANCE_SITE_PASSWORD is not set — site gate is off on this deploy.",
      },
      { status: 400 },
    );
  }

  const ip = clientIp(req);
  if (!consumeLoginAttempt(ip)) {
    return NextResponse.json(
      {
        error: "rate_limited",
        message: "Too many login attempts. Try again in a minute.",
      },
      { status: 429, headers: { "Retry-After": "60" } },
    );
  }

  const expected = sitePassword();
  if (!expected) {
    return NextResponse.json({ error: "misconfigured" }, { status: 500 });
  }

  let body: { password?: string } = {};
  try {
    body = (await req.json()) as { password?: string };
  } catch {
    return NextResponse.json(
      { error: "invalid_json", message: "Expected JSON body with password." },
      { status: 400 },
    );
  }

  const provided = typeof body.password === "string" ? body.password : "";
  if (!provided || !(await passwordsMatch(provided, expected))) {
    return NextResponse.json(
      { error: "unauthorized", message: "Incorrect password." },
      { status: 401 },
    );
  }

  const { token, expiresAt } = await mintSiteSessionToken(expected);
  const res = NextResponse.json({
    ok: true,
    expires_at: expiresAt,
  });
  res.cookies.set(SITE_AUTH_COOKIE, token, siteSessionCookieOptions(expiresAt));
  return res;
}
