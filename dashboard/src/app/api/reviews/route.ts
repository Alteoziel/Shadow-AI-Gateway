import { NextRequest, NextResponse } from "next/server";
import { listReviews, upsertReview, type StepResult } from "@/lib/store";

function authorize(req: NextRequest): boolean {
  const expected = process.env.GOVERNANCE_DASHBOARD_SECRET;
  if (!expected) {
    // Local/dev convenience: allow when secret unset
    return true;
  }
  return req.headers.get("x-governance-secret") === expected;
}

export async function GET() {
  const reviews = await listReviews();
  return NextResponse.json({ reviews });
}

export async function POST(req: NextRequest) {
  if (!authorize(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const body = await req.json();
  const review = await upsertReview({
    passed: Boolean(body.passed),
    pr_number: body.pr_number ?? null,
    commit_sha: body.commit_sha ?? null,
    repo: body.repo ?? null,
    steps: (body.steps ?? []) as StepResult[],
    summary: body.summary ?? {},
    status: "pending_review",
  });

  return NextResponse.json({ review }, { status: 201 });
}
