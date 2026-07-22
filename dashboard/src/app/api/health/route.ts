import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Minimal public health probe — no auth/config reconnaissance. */
export async function GET() {
  return NextResponse.json({ ok: true });
}
