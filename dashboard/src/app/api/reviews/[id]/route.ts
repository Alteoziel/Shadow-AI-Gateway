import { NextRequest, NextResponse } from "next/server";
import {
  getReview,
  updateReview,
  gradeComprehension,
  publicComprehension,
} from "@/lib/store";

type Params = { params: Promise<{ id: string }> };

export async function GET(_req: NextRequest, { params }: Params) {
  const { id } = await params;
  const review = await getReview(id);
  if (!review) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  return NextResponse.json({
    review: {
      ...review,
      // Never send answer keys to the client
      comprehension: publicComprehension(review.comprehension),
    },
  });
}

/**
 * Actions:
 * - submit_quiz — grade Step 6 comprehension (required before approve/merge)
 * - approve / reject / merge — Step 7 human panel (merge blocked until quiz passed)
 */
export async function POST(req: NextRequest, { params }: Params) {
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
          message: "No comprehension pack on this review yet. Re-run the guardrail suite.",
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

    // Return explanations only after submit
    const explanations = review.comprehension.questions.map((q) => ({
      id: q.id,
      correct: answers[q.id] === q.answer_index,
      explanation: q.explanation,
      expected_index: q.answer_index,
    }));

    return NextResponse.json({
      review: {
        ...updated,
        comprehension: publicComprehension(updated?.comprehension),
      },
      attempt,
      explanations,
    });
  }

  if (action === "reject") {
    const updated = await updateReview(id, {
      status: "rejected",
      reviewer_note: note,
    });
    return NextResponse.json({ review: updated });
  }

  if (action === "approve" || action === "merge") {
    if (review.comprehension && !review.comprehension_passed) {
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
    return NextResponse.json({ review: updated });
  }

  if (action === "merge") {
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
    if (!review.repo || !review.pr_number) {
      return NextResponse.json(
        { error: "missing_pr_metadata", message: "Review has no repo/PR number." },
        { status: 400 }
      );
    }

    const mergeUrl = `https://api.github.com/repos/${review.repo}/pulls/${review.pr_number}/merge`;
    const mergeResp = await fetch(mergeUrl, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        commit_title: `Merge PR #${review.pr_number} via AI Governance Panel`,
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
    return NextResponse.json({ review: updated, merge: mergeJson });
  }

  return NextResponse.json({ error: "unknown_action" }, { status: 400 });
}
