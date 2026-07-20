import { NextRequest, NextResponse } from "next/server";
import {
  authorizeIngest,
  unauthorizedResponse,
} from "@/lib/auth";
import { parseIngestBody } from "@/lib/ingest";
import {
  getStoreStatus,
  listReviews,
  upsertReview,
  sanitizeReviewForClient,
} from "@/lib/store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const reviews = await listReviews();
  return NextResponse.json({
    reviews: reviews.map(sanitizeReviewForClient),
    store: getStoreStatus(),
  });
}

export async function POST(req: NextRequest) {
  if (!authorizeIngest(req)) {
    return unauthorizedResponse("ingest");
  }

  const body = await req.json().catch(() => null);
  const parsed = parseIngestBody(body);
  if (!parsed.ok) {
    return NextResponse.json(
      { error: "invalid_payload", message: parsed.error },
      { status: 400 }
    );
  }

  const review = await upsertReview(parsed.data);

  return NextResponse.json(
    { review: sanitizeReviewForClient(review) },
    { status: 201 }
  );
}
