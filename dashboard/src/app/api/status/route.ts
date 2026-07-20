import { NextResponse } from "next/server";
import { dashboardAuthStatus } from "@/lib/auth";
import { getStoreStatus } from "@/lib/store";

export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json({
    auth: dashboardAuthStatus(),
    store: getStoreStatus(),
  });
}
