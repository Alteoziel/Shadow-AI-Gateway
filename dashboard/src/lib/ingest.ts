/**
 * Validate CI ingest payloads before they enter the review store.
 */

import { z } from "zod";
import type { StepResult } from "@/lib/store";
import { assertSafeEntrypoint } from "@/lib/codingSafety";

const MAX_STEPS = 32;
const MAX_FINDINGS = 200;
const MAX_STRING = 8_000;
const MAX_SUMMARY_KEYS = 64;

const findingSchema = z.object({
  step: z.string().max(128),
  severity: z.enum(["info", "warning", "error", "critical"]),
  message: z.string().max(MAX_STRING),
  file: z.string().max(1024).nullish(),
  line: z.number().int().nullish(),
  rule_id: z.string().max(128).nullish(),
  evidence: z.string().max(MAX_STRING).nullish(),
  suggestion: z.string().max(MAX_STRING).nullish(),
});

const codingTestSchema = z.object({
  id: z.string().max(64).optional(),
  args: z.array(z.unknown()).max(16),
  expected: z.unknown().optional(),
  raises: z.string().max(64).optional(),
});

const codingQuestionSchema = z.object({
  id: z.string().max(64),
  question_type: z.literal("coding").optional(),
  entrypoint: z.string().max(64),
  starter_code: z.string().max(32_768).optional(),
  tests: z.array(codingTestSchema).max(32),
  language: z.string().max(32).optional(),
  prompt: z.string().max(MAX_STRING).optional(),
  category: z.string().max(128).optional(),
  explanation: z.string().max(MAX_STRING).optional(),
  answer_index: z.number().optional(),
  choices: z.array(z.string().max(2000)).max(8).optional(),
});

const stepResultSchema = z.object({
  step: z.string().max(128),
  name: z.string().max(256),
  passed: z.boolean(),
  findings: z.array(findingSchema).max(MAX_FINDINGS).default([]),
  metrics: z.record(z.unknown()).optional(),
  skipped: z.boolean().optional(),
  skip_reason: z.string().max(MAX_STRING).nullish(),
});

const ingestSchema = z.object({
  passed: z.boolean(),
  pr_number: z.number().int().positive().nullish(),
  commit_sha: z
    .string()
    .regex(/^[0-9a-f]{7,40}$/i, "commit_sha must be a git SHA")
    .nullish(),
  repo: z
    .string()
    .regex(
      /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/,
      "repo must look like owner/name"
    )
    .nullish(),
  steps: z.array(stepResultSchema).max(MAX_STEPS).default([]),
  summary: z.record(z.unknown()).default({}),
});

export type IngestPayload = {
  passed: boolean;
  pr_number: number | null;
  commit_sha: string | null;
  repo: string | null;
  steps: StepResult[];
  summary: Record<string, unknown>;
};

function validateCodingEntrypoints(steps: StepResult[]): string | null {
  for (const step of steps) {
    const pack = step.metrics?.comprehension as
      | { questions?: unknown[] }
      | undefined;
    if (!pack?.questions) continue;
    for (const raw of pack.questions) {
      if (!raw || typeof raw !== "object") continue;
      const q = raw as { question_type?: string; entrypoint?: string };
      if (q.question_type !== "coding") continue;
      const parsed = codingQuestionSchema.safeParse(raw);
      if (!parsed.success) {
        return `Invalid coding question: ${parsed.error.issues[0]?.message}`;
      }
      const entryErr = assertSafeEntrypoint(parsed.data.entrypoint);
      if (entryErr) return entryErr;
    }
  }
  return null;
}

export function parseIngestBody(body: unknown):
  | { ok: true; data: IngestPayload }
  | { ok: false; error: string } {
  const parsed = ingestSchema.safeParse(body);
  if (!parsed.success) {
    return {
      ok: false,
      error: parsed.error.issues.map((i) => i.message).join("; "),
    };
  }
  const d = parsed.data;
  if (Object.keys(d.summary).length > MAX_SUMMARY_KEYS) {
    return { ok: false, error: `summary exceeds ${MAX_SUMMARY_KEYS} keys` };
  }
  const steps = d.steps as StepResult[];
  const codingErr = validateCodingEntrypoints(steps);
  if (codingErr) {
    return { ok: false, error: codingErr };
  }
  return {
    ok: true,
    data: {
      passed: d.passed,
      pr_number: d.pr_number ?? null,
      commit_sha: d.commit_sha ?? null,
      repo: d.repo ?? null,
      steps,
      summary: d.summary,
    },
  };
}
