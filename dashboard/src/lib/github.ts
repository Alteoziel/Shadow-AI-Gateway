/**
 * Safe GitHub merge URL construction.
 *
 * Validates owner/repo/PR before building the API URL so merge targets cannot
 * be redirected via tampered store data.
 */

const REPO_RE = /^([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)$/;

export type GithubRepoRef = {
  owner: string;
  name: string;
  full: string;
};

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

/**
 * Build a GitHub merge URL from validated components.
 * Prefer GITHUB_REPOSITORY (trusted env) when set; otherwise use the parsed repo.
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
