/**
 * Lightweight review store.
 *
 * Default: JSON file under .data/ (local / single-instance).
 * Optional: set DATABASE_URL to a Postgres connection string later
 * (Phase 3 of the gateway plan uses Supabase — same target).
 */

import { promises as fs } from "fs";
import path from "path";

export type Severity = "info" | "warning" | "error" | "critical";

export type Finding = {
  step: string;
  severity: Severity;
  message: string;
  file?: string | null;
  line?: number | null;
  rule_id?: string | null;
  evidence?: string | null;
  suggestion?: string | null;
};

export type StepResult = {
  step: string;
  name: string;
  passed: boolean;
  findings: Finding[];
  metrics?: Record<string, unknown>;
  skipped?: boolean;
  skip_reason?: string | null;
};

export type ReviewStatus = "pending_review" | "approved" | "rejected" | "merged";

export type Review = {
  id: string;
  createdAt: string;
  updatedAt: string;
  status: ReviewStatus;
  passed: boolean;
  pr_number?: number | null;
  commit_sha?: string | null;
  repo?: string | null;
  steps: StepResult[];
  summary: Record<string, unknown>;
  merge_sha?: string | null;
  reviewer_note?: string | null;
};

const DATA_DIR = path.join(process.cwd(), ".data");
const STORE_PATH = path.join(DATA_DIR, "reviews.json");

async function ensureStore(): Promise<Review[]> {
  await fs.mkdir(DATA_DIR, { recursive: true });
  try {
    const raw = await fs.readFile(STORE_PATH, "utf8");
    return JSON.parse(raw) as Review[];
  } catch {
    await fs.writeFile(STORE_PATH, "[]", "utf8");
    return [];
  }
}

async function writeStore(reviews: Review[]): Promise<void> {
  await fs.mkdir(DATA_DIR, { recursive: true });
  await fs.writeFile(STORE_PATH, JSON.stringify(reviews, null, 2), "utf8");
}

export async function listReviews(): Promise<Review[]> {
  const reviews = await ensureStore();
  return reviews.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export async function getReview(id: string): Promise<Review | null> {
  const reviews = await ensureStore();
  return reviews.find((r) => r.id === id) ?? null;
}

export async function upsertReview(
  payload: Omit<Review, "id" | "createdAt" | "updatedAt" | "status"> & {
    status?: ReviewStatus;
  }
): Promise<Review> {
  const reviews = await ensureStore();
  const now = new Date().toISOString();

  // Dedupe by repo+pr+commit when present
  const existingIdx = reviews.findIndex(
    (r) =>
      r.repo &&
      payload.repo &&
      r.pr_number &&
      payload.pr_number &&
      r.commit_sha &&
      payload.commit_sha &&
      r.repo === payload.repo &&
      r.pr_number === payload.pr_number &&
      r.commit_sha === payload.commit_sha
  );

  if (existingIdx >= 0) {
    const updated: Review = {
      ...reviews[existingIdx],
      ...payload,
      status: payload.status ?? reviews[existingIdx].status,
      updatedAt: now,
    };
    reviews[existingIdx] = updated;
    await writeStore(reviews);
    return updated;
  }

  const review: Review = {
    id: `rev_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`,
    createdAt: now,
    updatedAt: now,
    status: payload.status ?? "pending_review",
    passed: payload.passed,
    pr_number: payload.pr_number,
    commit_sha: payload.commit_sha,
    repo: payload.repo,
    steps: payload.steps,
    summary: payload.summary,
  };
  reviews.unshift(review);
  await writeStore(reviews);
  return review;
}

export async function updateReview(
  id: string,
  patch: Partial<Review>
): Promise<Review | null> {
  const reviews = await ensureStore();
  const idx = reviews.findIndex((r) => r.id === id);
  if (idx < 0) return null;
  reviews[idx] = {
    ...reviews[idx],
    ...patch,
    updatedAt: new Date().toISOString(),
  };
  await writeStore(reviews);
  return reviews[idx];
}
