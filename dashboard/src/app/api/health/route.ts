import { NextResponse } from "next/server";
import { getStoreStatus } from "@/lib/store";
import { dashboardSecretConfigured } from "@/lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const store = getStoreStatus();
  return NextResponse.json({
    ok: true,
    store,
    dashboard_secret_configured: dashboardSecretConfigured(),
    vercel: Boolean(process.env.VERCEL),
  });
}
