/**
 * Lightweight review store.
 *
 * Default: JSON file under .data/ (local / single-instance).
 * Optional: set DATABASE_URL to a Postgres connection string later
 * (Phase 3 of the gateway plan uses Supabase — same target).
 */

import { createHash } from "crypto";
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
    steps: sanitizeStepsForClient(review.steps),
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
  const comprehension = extractComprehension(payload.steps);
  const fingerprint = comprehensionFingerprint(comprehension);
  // Always require comprehension when a pack exists; if missing, stay pending_comprehension
  const initialStatus: ReviewStatus =
    payload.status ??
    (comprehension ? "pending_comprehension" : "pending_comprehension");

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

    const updated: Review = {
      ...prev,
      ...payload,
      comprehension,
      comprehension_fingerprint: fingerprint,
      // Reset quiz whenever the question pack changes (even on same commit / CI re-run)
      comprehension_passed: keepPass,
      comprehension_attempt: keepPass ? prev.comprehension_attempt : null,
      status:
        payload.status ??
        (prev.status === "merged"
          ? "merged"
          : keepPass
            ? "pending_review"
            : "pending_comprehension"),
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
