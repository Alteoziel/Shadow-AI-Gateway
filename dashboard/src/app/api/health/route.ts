import { NextResponse } from "next/server";
import { getStoreStatus } from "@/lib/store";
import { dashboardSecretConfigured } from "@/lib/auth";
import { siteGateEnabled } from "@/lib/siteAuth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const store = getStoreStatus();
  return NextResponse.json({
    ok: true,
    store,
    dashboard_secret_configured: dashboardSecretConfigured(),
    site_gate_enabled: siteGateEnabled(),
    vercel: Boolean(process.env.VERCEL),
  });
}
