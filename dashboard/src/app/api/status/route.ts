import { NextResponse } from "next/server";
import { dashboardAuthStatus } from "@/lib/auth";
import { REVIEW_STORE_PATH } from "@/lib/store";

export async function GET() {
  return NextResponse.json({
    auth: dashboardAuthStatus(),
    store: {
      type: "json",
      path: REVIEW_STORE_PATH,
    },
  });
}
