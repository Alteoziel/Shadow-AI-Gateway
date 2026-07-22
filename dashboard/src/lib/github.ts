/**
 * Safe GitHub URL helpers + Governance Quiz commit status.
 *
 * Branch protection can require context {@link QUIZ_STATUS_CONTEXT}.
 * CI sets it to pending; the dashboard sets success/failure after the quiz.
 */

const REPO_RE = /^([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)$/;

/** Must match the name you require under branch protection. */
export const QUIZ_STATUS_CONTEXT = "Governance Quiz";

export type GithubRepoRef = {
  owner: string;
  name: string;
  full: string;
};

export type QuizStatusState = "pending" | "success" | "failure" | "error";

export function parseGithubRepo(repo: string | null | undefined): GithubRepoRef | null {
  if (!repo || typeof repo !== "string") return null;
  const match = REPO_RE.exec(repo.trim());
  if (!match) return null;
  return { owner: match[1], name: match[2], full: `${match[1]}/${match[2]}` };
}

export function parsePositiveInt(value: unknown): number | null {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isInteger(n) || n <= 0) return null;
  return n;
}

export function parseCommitSha(sha: string | null | undefined): string | null {
  if (!sha || typeof sha !== "string") return null;
  const trimmed = sha.trim();
  if (!/^[0-9a-f]{7,40}$/i.test(trimmed)) return null;
  return trimmed;
}

function githubToken(): string | null {
  return (
    process.env.GITHUB_TOKEN?.trim() ||
    process.env.GH_MERGE_TOKEN?.trim() ||
    process.env.GH_STATUS_TOKEN?.trim() ||
    null
  );
}

/**
 * Build a GitHub merge URL from validated components.
 * GITHUB_REPOSITORY is required in production/Vercel; otherwise use the parsed repo.
 */
export function buildPullMergeUrl(
  repo: string | null | undefined,
  prNumber: unknown
): { url: string; repo: string; pr: number } | { error: string } {
  const parsed = parseGithubRepo(repo);
  if (!parsed) {
    return { error: "Review repo must look like owner/name." };
  }

  const allowed = process.env.GITHUB_REPOSITORY?.trim();
  const prodLike =
    process.env.NODE_ENV === "production" || process.env.VERCEL === "1";
  if (prodLike && !allowed) {
    return {
      error:
        "GITHUB_REPOSITORY must be set in production to pin merge targets.",
    };
  }
  if (allowed) {
    const allowedParsed = parseGithubRepo(allowed);
    if (!allowedParsed || allowedParsed.full !== parsed.full) {
      return {
        error: `Review repo ${parsed.full} is not allowed (expected ${allowed}).`,
      };
    }
  }

  const pr = parsePositiveInt(prNumber);
  if (pr === null) {
    return { error: "Review has no valid PR number." };
  }

  return {
    url: `https://api.github.com/repos/${parsed.owner}/${parsed.name}/pulls/${pr}/merge`,
    repo: parsed.full,
    pr,
  };
}

/**
 * Post/replace the Governance Quiz commit status for branch protection.
 * Soft-fails when token/repo/sha are missing — quiz UI still works.
 */
export async function setGovernanceQuizStatus(input: {
  repo: string | null | undefined;
  commitSha: string | null | undefined;
  state: QuizStatusState;
  description: string;
  targetUrl?: string | null;
}): Promise<{ ok: true } | { ok: false; error: string }> {
  const token = githubToken();
  if (!token) {
    return {
      ok: false,
      error:
        "No GITHUB_TOKEN / GH_MERGE_TOKEN / GH_STATUS_TOKEN — cannot update Governance Quiz check.",
    };
  }

  const parsed = parseGithubRepo(input.repo);
  if (!parsed) {
    return { ok: false, error: "Review repo must look like owner/name." };
  }

  const allowed = process.env.GITHUB_REPOSITORY?.trim();
  const prodLike =
    process.env.NODE_ENV === "production" || process.env.VERCEL === "1";
  if (prodLike && !allowed) {
    return {
      ok: false,
      error:
        "GITHUB_REPOSITORY must be set in production to pin status targets.",
    };
  }
  if (allowed) {
    const allowedParsed = parseGithubRepo(allowed);
    if (!allowedParsed || allowedParsed.full !== parsed.full) {
      return {
        ok: false,
        error: `Review repo ${parsed.full} is not allowed (expected ${allowed}).`,
      };
    }
  }

  const sha = parseCommitSha(input.commitSha);
  if (!sha) {
    return { ok: false, error: "Review has no valid commit SHA." };
  }

  const url = `https://api.github.com/repos/${parsed.owner}/${parsed.name}/statuses/${sha}`;
  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({
        state: input.state,
        context: QUIZ_STATUS_CONTEXT,
        description: input.description.slice(0, 140),
        ...(input.targetUrl
          ? { target_url: input.targetUrl.slice(0, 1024) }
          : {}),
      }),
    });
    if (!resp.ok) {
      const details = await resp.text().catch(() => "");
      return {
        ok: false,
        error: `GitHub status API ${resp.status}: ${details.slice(0, 200)}`,
      };
    }
    return { ok: true };
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err.message : "status update failed",
    };
  }
}

export function dashboardReviewUrl(reviewId: string): string | null {
  const base =
    process.env.GOVERNANCE_DASHBOARD_PUBLIC_URL?.trim() ||
    process.env.VERCEL_PROJECT_PRODUCTION_URL?.trim() ||
    process.env.VERCEL_URL?.trim() ||
    null;
  if (!base) return null;
  const host = base.startsWith("http") ? base : `https://${base}`;
  return `${host.replace(/\/$/, "")}/?id=${encodeURIComponent(reviewId)}`;
}
