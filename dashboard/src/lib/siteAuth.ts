/**
 * Browser site gate (separate from CI/reviewer X-Governance-* secrets).
 *
 * When GOVERNANCE_SITE_PASSWORD is set, visitors need a valid httpOnly cookie
 * minted at /login. Cookie lasts SITE_SESSION_MAX_AGE_SEC (7 days).
 */

export const SITE_AUTH_COOKIE = "governance_site_session";
export const SITE_SESSION_MAX_AGE_SEC = 60 * 60 * 24 * 7; // 7 days

const COOKIE_VERSION = "v1";

export function sitePassword(): string | null {
  const value = process.env.GOVERNANCE_SITE_PASSWORD?.trim();
  return value ? value : null;
}

export function siteGateEnabled(): boolean {
  return sitePassword() !== null;
}

function encoder() {
  return new TextEncoder();
}

async function hmacHex(key: string, message: string): Promise<string> {
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    encoder().encode(key),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign(
    "HMAC",
    cryptoKey,
    encoder().encode(message),
  );
  return [...new Uint8Array(sig)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function signingKey(password: string): string {
  // Bind cookie to the site password so rotation invalidates sessions.
  return `governance-site-gate:${password}`;
}

export function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) {
    out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return out === 0;
}

export async function passwordsMatch(
  provided: string,
  expected: string,
): Promise<boolean> {
  // Hash both sides so length differences do not short-circuit comparison.
  const [left, right] = await Promise.all([
    hmacHex("password-compare", provided),
    hmacHex("password-compare", expected),
  ]);
  return timingSafeEqual(left, right);
}

/** Mint a signed session cookie value valid until expiresAt (unix seconds). */
export async function mintSiteSessionToken(
  password: string,
  nowSec = Math.floor(Date.now() / 1000),
): Promise<{ token: string; expiresAt: number }> {
  const expiresAt = nowSec + SITE_SESSION_MAX_AGE_SEC;
  const payload = `${COOKIE_VERSION}.${expiresAt}`;
  const sig = await hmacHex(signingKey(password), payload);
  return { token: `${payload}.${sig}`, expiresAt };
}

export async function verifySiteSessionToken(
  token: string | undefined | null,
  password: string,
  nowSec = Math.floor(Date.now() / 1000),
): Promise<boolean> {
  if (!token) return false;
  const parts = token.split(".");
  if (parts.length !== 3) return false;
  const [version, expiresRaw, sig] = parts;
  if (version !== COOKIE_VERSION) return false;
  const expiresAt = Number(expiresRaw);
  if (!Number.isFinite(expiresAt) || expiresAt <= nowSec) return false;
  // Reject absurd far-future cookies (clock skew / tampering).
  if (expiresAt > nowSec + SITE_SESSION_MAX_AGE_SEC + 60) return false;
  const payload = `${version}.${expiresRaw}`;
  const expected = await hmacHex(signingKey(password), payload);
  return timingSafeEqual(sig, expected);
}

export function siteSessionCookieOptions(expiresAt: number) {
  return {
    httpOnly: true as const,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    expires: new Date(expiresAt * 1000),
  };
}
