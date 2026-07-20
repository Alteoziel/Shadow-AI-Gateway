import { NextRequest, NextResponse } from "next/server";
import { getReview, updateReview } from "@/lib/store";

type Params = { params: Promise<{ id: string }> };

export async function GET(_req: NextRequest, { params }: Params) {
  const { id } = await params;
  const review = await getReview(id);
  if (!review) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  return NextResponse.json({ review });
}

/**
 * Approve + merge via GitHub REST API.
 * Requires GITHUB_TOKEN with contents:write + pull-requests:write on the repo.
 */
export async function POST(req: NextRequest, { params }: Params) {
  const { id } = await params;
  const review = await getReview(id);
  if (!review) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  const body = await req.json().catch(() => ({}));
  const action = body.action as "approve" | "reject" | "merge";
  const note = (body.note as string) || null;

  if (action === "reject") {
    const updated = await updateReview(id, {
      status: "rejected",
      reviewer_note: note,
    });
    return NextResponse.json({ review: updated });
  }

  if (action === "approve") {
    const updated = await updateReview(id, {
      status: "approved",
      reviewer_note: note,
    });
    return NextResponse.json({ review: updated });
  }

  if (action === "merge") {
    // Manual override routing: allow merge even if suite failed when reviewer insists
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
