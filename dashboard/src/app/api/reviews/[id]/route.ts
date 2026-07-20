import { NextRequest, NextResponse } from "next/server";
import {
  authorizeReviewer,
  unauthorizedResponse,
} from "@/lib/auth";
import { buildPullMergeUrl } from "@/lib/github";
import {
  getReview,
  updateReview,
  gradeComprehension,
  sanitizeReviewForClient,
} from "@/lib/store";

type Params = { params: Promise<{ id: string }> };

export async function GET(_req: NextRequest, { params }: Params) {
  const { id } = await params;
  const review = await getReview(id);
  if (!review) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  return NextResponse.json({
    review: sanitizeReviewForClient(review),
  });
}

/**
 * Actions:
 * - submit_quiz — grade Step 6 comprehension (required before approve/merge)
 * - approve / reject / merge — Step 7 human panel
 *
 * All mutations require reviewer auth (X-Governance-Reviewer-Secret).
 */
export async function POST(req: NextRequest, { params }: Params) {
  if (!authorizeReviewer(req)) {
    return unauthorizedResponse("reviewer");
  }

  const { id } = await params;
  const review = await getReview(id);
  if (!review) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  const body = await req.json().catch(() => ({}));
  const action = body.action as
    | "approve"
    | "reject"
    | "merge"
    | "submit_quiz";
  const note = (body.note as string) || null;

  if (action === "submit_quiz") {
    if (!review.comprehension) {
      return NextResponse.json(
        {
          error: "no_quiz",
          message:
            "No comprehension pack on this review yet. Re-run the guardrail suite.",
        },
        { status: 400 }
      );
    }
    const answers = (body.answers ?? {}) as Record<string, number>;
    const attempt = gradeComprehension(review.comprehension, answers);
    const updated = await updateReview(id, {
      comprehension_passed: attempt.passed,
      comprehension_attempt: attempt,
      status: attempt.passed ? "pending_review" : "pending_comprehension",
      reviewer_note: note,
    });

    // Teach with explanations, but never leak expected_index (anti-cheat)
    const explanations = review.comprehension.questions.map((q) => ({
      id: q.id,
      correct: answers[q.id] === q.answer_index,
      explanation: q.explanation,
    }));

    return NextResponse.json({
      review: updated ? sanitizeReviewForClient(updated) : null,
      attempt,
      explanations,
    });
  }

  if (action === "reject") {
    const updated = await updateReview(id, {
      status: "rejected",
      reviewer_note: note,
    });
    return NextResponse.json({
      review: updated ? sanitizeReviewForClient(updated) : null,
    });
  }

  if (action === "approve" || action === "merge") {
    // Always require a quiz pack + pass — missing pack is not a free bypass
    if (!review.comprehension) {
      return NextResponse.json(
        {
          error: "comprehension_required",
          message:
            "No comprehension quiz on this review. Re-run the AI Guardrail suite " +
            "so Step 6 can generate a study guide + quiz before approving or merging.",
        },
        { status: 403 }
      );
    }
    if (!review.comprehension_passed) {
      return NextResponse.json(
        {
          error: "comprehension_required",
          message:
            "Pass the Step 6 comprehension quiz before approving or merging. " +
            "You should understand the change — vocabulary, flow, dependencies, " +
            "manual tasks, and security — before shipping.",
        },
        { status: 403 }
      );
    }
  }

  if (action === "approve") {
    const updated = await updateReview(id, {
      status: "approved",
      reviewer_note: note,
    });
    return NextResponse.json({
      review: updated ? sanitizeReviewForClient(updated) : null,
    });
  }

  if (action === "merge") {
    // Do not squash-merge when automated suite failed
    if (!review.passed) {
      return NextResponse.json(
        {
          error: "suite_failed",
          message:
            "Automated guardrail suite failed. Fix blocking findings (or reject " +
            "the PR) before merging. Comprehension alone is not enough.",
        },
        { status: 403 }
      );
    }

    const token = process.env.GITHUB_TOKEN || process.env.GH_MERGE_TOKEN;
    if (!token) {
      return NextResponse.json(
        {
          error: "missing_github_token",
          message:
            "Set GITHUB_TOKEN (or GH_MERGE_TOKEN) on the dashboard host to enable merges.",
        },
        { status: 400 }
      );
    }
    const mergeTarget = buildPullMergeUrl(review.repo, review.pr_number);
    if ("error" in mergeTarget) {
      return NextResponse.json(
        {
          error: "missing_pr_metadata",
          message: mergeTarget.error,
        },
        { status: 400 }
      );
    }

    const mergeResp = await fetch(mergeTarget.url, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        commit_title: `Merge PR #${mergeTarget.pr} via AI Governance Panel`,
        merge_method: "squash",
      }),
    });

    const mergeJson = await mergeResp.json().catch(() => ({}));
    if (!mergeResp.ok) {
      return NextResponse.json(
        { error: "github_merge_failed", details: mergeJson },
        { status: 502 }
      );
    }

    const updated = await updateReview(id, {
      status: "merged",
      merge_sha: mergeJson.sha ?? null,
      reviewer_note: note,
    });
    return NextResponse.json({
      review: updated ? sanitizeReviewForClient(updated) : null,
      merge: mergeJson,
    });
  }

  return NextResponse.json({ error: "unknown_action" }, { status: 400 });
}
