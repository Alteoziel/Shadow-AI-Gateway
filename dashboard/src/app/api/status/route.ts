import { NextRequest, NextResponse } from "next/server";
import { dashboardAuthStatus, unauthorizedResponse } from "@/lib/auth";
import { getStoreStatus } from "@/lib/store";
import { authorizeReviewRead } from "@/lib/reviewAuth";

export async function GET(req: NextRequest) {
  if (!(await authorizeReviewRead(req))) {
    return unauthorizedResponse("ingest");
  }
  return NextResponse.json({
    auth: dashboardAuthStatus(),
    store: getStoreStatus(),
  });
}
