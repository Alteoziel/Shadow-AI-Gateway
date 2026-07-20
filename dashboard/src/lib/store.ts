/**
 * Lightweight review store.
 *
 * Priority:
 * 1. Upstash Redis / Vercel KV (durable on serverless) — preferred on Vercel
 * 2. JSON file — local `.data/`, or `/tmp` when `VERCEL` is set (ephemeral)
 *
 * Reads never throw to the UI: callers get [] + optional setup error via
 * `getStoreStatus()`. Writes throw only when no backend can persist.
 */

import { createHash } from "crypto";
import { promises as fs } from "fs";
import path from "path";
import { Redis } from "@upstash/redis";

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

export type QuizQuestion = {
  id: string;
  category: string;
  category_label?: string;
  prompt: string;
  choices: string[];
  answer_index: number;
  explanation: string;
};

export type ComprehensionPack = {
  learner_level?: string;
  pass_threshold: number;
  generator?: string;
  study_guide: {
    elevator_pitch: string;
    bigger_picture: string;
    glossary: { term: string; definition: string }[];
    key_functions: { name: string; file: string; plain_english: string }[];
    dependencies: string[];
    manual_dev_tasks: string[];
    security_notes: string[];
    files_touched?: string[];
  };
  questions: QuizQuestion[];
};

export type ComprehensionAttempt = {
  score: number;
  correct: number;
  total: number;
  passed: boolean;
  threshold: number;
  at: string;
};

export type ReviewStatus =
  | "pending_comprehension"
  | "pending_review"
  | "approved"
  | "rejected"
  | "merged";

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
  comprehension?: ComprehensionPack | null;
  comprehension_passed?: boolean;
  comprehension_attempt?: ComprehensionAttempt | null;
  comprehension_fingerprint?: string | null;
};

export type StoreStatus = {
  backend: "redis" | "file";
  durable: boolean;
  warning: string | null;
};

const REDIS_KEY = "governance:reviews";

function isVercel(): boolean {
  return Boolean(process.env.VERCEL);
}

function fileStorePath(): string {
  // Vercel serverless FS is read-only except /tmp
  if (isVercel()) {
    return path.join("/tmp", "governance-reviews.json");
  }
  return path.join(process.cwd(), ".data", "reviews.json");
}

function redisClient(): Redis | null {
  const url = (
    process.env.UPSTASH_REDIS_REST_URL ||
    process.env.KV_REST_API_URL ||
    ""
  ).trim();
  const token = (
    process.env.UPSTASH_REDIS_REST_TOKEN ||
    process.env.KV_REST_API_TOKEN ||
    ""
  ).trim();
  if (!url || !token) return null;
  return new Redis({ url, token });
}

export function getStoreStatus(): StoreStatus {
  if (redisClient()) {
    return { backend: "redis", durable: true, warning: null };
  }
  if (isVercel()) {
    return {
      backend: "file",
      durable: false,
      warning:
        "Running on Vercel without Upstash Redis. Quiz data is stored in /tmp and will not survive across serverless instances. Add Upstash Redis (Storage tab) and set UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN (or KV_REST_API_*), then redeploy.",
    };
  }
  return { backend: "file", durable: true, warning: null };
}

async function readFileReviews(): Promise<Review[]> {
  const storePath = fileStorePath();
  await fs.mkdir(path.dirname(storePath), { recursive: true });
  try {
    const raw = await fs.readFile(storePath, "utf8");
    const parsed = JSON.parse(raw) as Review[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    await fs.writeFile(storePath, "[]", "utf8");
    return [];
  }
}

async function writeFileReviews(reviews: Review[]): Promise<void> {
  const storePath = fileStorePath();
  await fs.mkdir(path.dirname(storePath), { recursive: true });
  await fs.writeFile(storePath, JSON.stringify(reviews, null, 2), "utf8");
}

async function readReviews(): Promise<Review[]> {
  const redis = redisClient();
  if (redis) {
    const data = await redis.get<Review[] | string>(REDIS_KEY);
    if (Array.isArray(data)) return data;
    if (typeof data === "string") {
      try {
        const parsed = JSON.parse(data) as Review[];
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    }
    return [];
  }
  return readFileReviews();
}

async function writeReviews(reviews: Review[]): Promise<void> {
  const redis = redisClient();
  if (redis) {
    await redis.set(REDIS_KEY, reviews);
    return;
  }
  await writeFileReviews(reviews);
}

export function extractComprehension(
  steps: StepResult[]
): ComprehensionPack | null {
  const step = steps.find((s) => s.step === "comprehension_gate");
  const pack = step?.metrics?.comprehension;
  if (!pack || typeof pack !== "object") return null;
  return pack as ComprehensionPack;
}

export function comprehensionFingerprint(
  pack: ComprehensionPack | null | undefined
): string | null {
  if (!pack?.questions?.length) return null;
  const material = pack.questions
    .map((q) => `${q.id}:${q.prompt}:${q.choices.join("|")}`)
    .join("\n");
  return createHash("sha256").update(material).digest("hex").slice(0, 16);
}

/** Strip answer keys from a comprehension pack. */
export function publicComprehension(pack: ComprehensionPack | null | undefined) {
  if (!pack) return null;
  return {
    learner_level: pack.learner_level,
    pass_threshold: pack.pass_threshold,
    generator: pack.generator,
    study_guide: pack.study_guide,
    questions: pack.questions.map(
      ({ answer_index: _a, explanation: _e, ...rest }) => rest
    ),
  };
}

/** Strip answer keys from steps[].metrics.comprehension too. */
export function sanitizeStepsForClient(steps: StepResult[]): StepResult[] {
  return steps.map((step) => {
    if (step.step !== "comprehension_gate" || !step.metrics?.comprehension) {
      return step;
    }
    const metrics = { ...step.metrics };
    metrics.comprehension = publicComprehension(
      step.metrics.comprehension as ComprehensionPack
    );
    return { ...step, metrics };
  });
}

/** Full client-safe review (no answer keys anywhere). */
export function sanitizeReviewForClient(review: Review): Review {
  return {
    ...review,
    comprehension: publicComprehension(
      review.comprehension
    ) as Review["comprehension"],
    steps: sanitizeStepsForClient(review.steps ?? []),
  };
}

export function gradeComprehension(
  pack: ComprehensionPack,
  answers: Record<string, number>
): ComprehensionAttempt {
  const total = pack.questions.length;
  let correct = 0;
  for (const q of pack.questions) {
    if (answers[q.id] === q.answer_index) correct += 1;
  }
  const score = total ? correct / total : 0;
  const threshold = pack.pass_threshold ?? 0.8;
  return {
    score,
    correct,
    total,
    passed: score >= threshold,
    threshold,
    at: new Date().toISOString(),
  };
}

export async function listReviews(): Promise<Review[]> {
  try {
    const reviews = await readReviews();
    return reviews.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  } catch (err) {
    console.error("[governance-store] listReviews failed", err);
    return [];
  }
}

export async function getReview(id: string): Promise<Review | null> {
  try {
    const reviews = await readReviews();
    return reviews.find((r) => r.id === id) ?? null;
  } catch (err) {
    console.error("[governance-store] getReview failed", err);
    return null;
  }
}

export async function upsertReview(
  payload: Omit<Review, "id" | "createdAt" | "updatedAt" | "status"> & {
    status?: ReviewStatus;
  }
): Promise<Review> {
  const reviews = await readReviews();
  const now = new Date().toISOString();
  const comprehension = extractComprehension(payload.steps);
  const fingerprint = comprehensionFingerprint(comprehension);
  const initialStatus: ReviewStatus =
    payload.status ?? "pending_comprehension";

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
    const prev = reviews[existingIdx];
    const sameQuiz =
      Boolean(fingerprint) &&
      fingerprint === prev.comprehension_fingerprint &&
      prev.commit_sha === payload.commit_sha;
    const keepPass = sameQuiz && Boolean(prev.comprehension_passed);

    let nextStatus: ReviewStatus;
    if (payload.status) {
      nextStatus = payload.status;
    } else if (prev.status === "merged") {
      nextStatus = "merged";
    } else if (!sameQuiz) {
      nextStatus = "pending_comprehension";
    } else if (prev.status === "approved" || prev.status === "rejected") {
      nextStatus = prev.status;
    } else {
      nextStatus = keepPass ? "pending_review" : "pending_comprehension";
    }

    const updated: Review = {
      ...prev,
      ...payload,
      comprehension,
      comprehension_fingerprint: fingerprint,
      comprehension_passed: keepPass,
      comprehension_attempt: keepPass ? prev.comprehension_attempt : null,
      status: nextStatus,
      updatedAt: now,
    };
    reviews[existingIdx] = updated;
    await writeReviews(reviews);
    return updated;
  }

  const review: Review = {
    id: `rev_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`,
    createdAt: now,
    updatedAt: now,
    status: initialStatus,
    passed: payload.passed,
    pr_number: payload.pr_number,
    commit_sha: payload.commit_sha,
    repo: payload.repo,
    steps: payload.steps,
    summary: payload.summary,
    comprehension,
    comprehension_fingerprint: fingerprint,
    comprehension_passed: false,
    comprehension_attempt: null,
  };
  reviews.unshift(review);
  await writeReviews(reviews);
  return review;
}

export async function updateReview(
  id: string,
  patch: Partial<Review>
): Promise<Review | null> {
  const reviews = await readReviews();
  const idx = reviews.findIndex((r) => r.id === id);
  if (idx < 0) return null;
  reviews[idx] = {
    ...reviews[idx],
    ...patch,
    updatedAt: new Date().toISOString(),
  };
  await writeReviews(reviews);
  return reviews[idx];
}
