import { NextRequest, NextResponse } from "next/server";
import {
  authorizeIngest,
  isProductionLike,
  unauthorizedResponse,
} from "@/lib/auth";
import { parseIngestBody } from "@/lib/ingest";
import {
  dashboardReviewUrl,
  setGovernanceQuizStatus,
} from "@/lib/github";
import {
  getStoreStatus,
  listReviews,
  upsertReview,
  sanitizeReviewForClient,
} from "@/lib/store";
import {
  authorizeReviewRead,
  siteGateMisconfiguredResponse,
} from "@/lib/reviewAuth";
import { siteGateEnabled } from "@/lib/siteAuth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  if (isProductionLike() && !siteGateEnabled()) {
    // Machine auth can still list; otherwise fail closed.
    if (!authorizeIngest(req)) {
      return siteGateMisconfiguredResponse();
    }
  }
  if (!(await authorizeReviewRead(req))) {
    return unauthorizedResponse("ingest");
  }

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

  // Keep the branch-protection check in sync with quiz state for this SHA.
  const quizStatus = await setGovernanceQuizStatus({
    repo: review.repo,
    commitSha: review.commit_sha,
    state: review.comprehension_passed ? "success" : "pending",
    description: review.comprehension_passed
      ? "Comprehension quiz passed for this commit."
      : "Take the Step 6 comprehension quiz on the governance dashboard.",
    targetUrl: dashboardReviewUrl(review.id),
  });

  return NextResponse.json(
    {
      review: sanitizeReviewForClient(review),
      quiz_status: quizStatus,
    },
    { status: 201 }
  );
}
