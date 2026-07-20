import { NextRequest, NextResponse } from "next/server";
import {
  authorizeIngest,
  unauthorizedResponse,
} from "@/lib/auth";
import {
  getStoreStatus,
  listReviews,
  upsertReview,
  sanitizeReviewForClient,
  type StepResult,
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

  const body = await req.json();
  const review = await upsertReview({
    passed: Boolean(body.passed),
    pr_number: body.pr_number ?? null,
    commit_sha: body.commit_sha ?? null,
    repo: body.repo ?? null,
    steps: (body.steps ?? []) as StepResult[],
    summary: body.summary ?? {},
  });

  return NextResponse.json(
    { review: sanitizeReviewForClient(review) },
    { status: 201 }
  );
}
