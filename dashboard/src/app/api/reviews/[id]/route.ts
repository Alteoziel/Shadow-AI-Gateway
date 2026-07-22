import { NextRequest, NextResponse } from "next/server";
import {
  authorizeIngest,
  authorizeReviewer,
  isProductionLike,
  unauthorizedResponse,
} from "@/lib/auth";
import {
  buildPullMergeUrl,
  dashboardReviewUrl,
  setGovernanceQuizStatus,
} from "@/lib/github";
import {
  getReview,
  updateReview,
  updateReviewConditional,
  gradeComprehension,
  sanitizeReviewForClient,
} from "@/lib/store";
import {
  authorizeReviewRead,
  siteGateMisconfiguredResponse,
} from "@/lib/reviewAuth";
import { siteGateEnabled } from "@/lib/siteAuth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Params = { params: Promise<{ id: string }> };

const MAX_CODING_SOURCE = 32_768;
const TERMINAL_STATUSES = new Set(["approved", "merged", "rejected"]);

export async function GET(req: NextRequest, { params }: Params) {
  if (isProductionLike() && !siteGateEnabled()) {
    if (!authorizeIngest(req) && !authorizeReviewer(req)) {
      return siteGateMisconfiguredResponse();
    }
  }
  if (!(await authorizeReviewRead(req))) {
    return unauthorizedResponse("ingest");
  }

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
    if (TERMINAL_STATUSES.has(review.status)) {
      return NextResponse.json(
        {
          error: "invalid_state",
          message: `Cannot retake quiz when review status is ${review.status}.`,
        },
        { status: 409 }
      );
    }
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
    const codingSubmissions = (body.coding_submissions ?? {}) as Record<
      string,
      string
    >;
    for (const [qid, src] of Object.entries(codingSubmissions)) {
      if (typeof src !== "string") {
        return NextResponse.json(
          { error: "invalid_coding_submission", message: `Bad source for ${qid}` },
          { status: 400 }
        );
      }
      if (Buffer.byteLength(src, "utf8") > MAX_CODING_SOURCE) {
        return NextResponse.json(
          {
            error: "coding_source_too_large",
            message: `Coding submission for ${qid} exceeds ${MAX_CODING_SOURCE} bytes.`,
          },
          { status: 413 }
        );
      }
    }
    const attempt = gradeComprehension(
      review.comprehension,
      answers,
      codingSubmissions
    );
    const updated = await updateReview(id, {
      comprehension_passed: attempt.passed,
      comprehension_attempt: attempt,
      status: attempt.passed ? "pending_review" : "pending_comprehension",
      reviewer_note: note,
    });

    const quizStatus = await setGovernanceQuizStatus({
      repo: review.repo,
      commitSha: review.commit_sha,
      state: attempt.passed ? "success" : "failure",
      description: attempt.passed
        ? `Quiz passed (${attempt.correct}/${attempt.total}).`
        : `Quiz failed (${attempt.correct}/${attempt.total}) — retake required.`,
      targetUrl: dashboardReviewUrl(id),
    });

    // Teach with explanations, but never leak expected_index (anti-cheat)
    const explanations = review.comprehension.questions.map((q) => {
      if (q.question_type === "coding") {
        const c = attempt.coding?.[q.id];
        return {
          id: q.id,
          correct: Boolean(c?.passed),
          explanation: q.explanation,
          coding: c
            ? {
                passed: c.passed,
                passedTests: c.passedTests,
                totalTests: c.totalTests,
                errors: c.errors,
              }
            : null,
        };
      }
      return {
        id: q.id,
        correct: answers[q.id] === q.answer_index,
        explanation: q.explanation,
      };
    });

    return NextResponse.json({
      review: updated ? sanitizeReviewForClient(updated) : null,
      attempt: {
        score: attempt.score,
        correct: attempt.correct,
        total: attempt.total,
        passed: attempt.passed,
        threshold: attempt.threshold,
        at: attempt.at,
      },
      explanations,
      quiz_status: quizStatus,
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
    const updated = await updateReviewConditional(
      id,
      (current) =>
        Boolean(current.comprehension) &&
        Boolean(current.comprehension_passed) &&
        current.status !== "merged",
      {
        status: "approved",
        reviewer_note: note,
      }
    );
    if (!updated) {
      return NextResponse.json(
        {
          error: "comprehension_required",
          message:
            "Approve blocked: comprehension must still be passed (concurrent update?).",
        },
        { status: 409 }
      );
    }
    return NextResponse.json({
      review: sanitizeReviewForClient(updated),
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

    const mergeJson = (await mergeResp.json().catch(() => ({}))) as {
      sha?: string;
      message?: string;
    };
    if (!mergeResp.ok) {
      return NextResponse.json(
        {
          error: "github_merge_failed",
          message:
            typeof mergeJson.message === "string"
              ? mergeJson.message.slice(0, 200)
              : "GitHub merge failed",
          github_status: mergeResp.status,
        },
        { status: 502 }
      );
    }

    const updated = await updateReviewConditional(
      id,
      (current) =>
        Boolean(current.comprehension_passed) &&
        current.passed === true &&
        current.status !== "merged",
      {
        status: "merged",
        merge_sha: mergeJson.sha ?? null,
        reviewer_note: note,
      }
    );
    if (!updated) {
      return NextResponse.json(
        {
          error: "invalid_state",
          message: "Merge blocked by concurrent state change.",
        },
        { status: 409 }
      );
    }
    return NextResponse.json({
      review: sanitizeReviewForClient(updated),
      merge: { sha: mergeJson.sha ?? null, ok: true },
    });
  }

  return NextResponse.json({ error: "unknown_action" }, { status: 400 });
}
