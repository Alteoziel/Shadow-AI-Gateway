/**
 * Validate CI ingest payloads before they enter the review store.
 */

import { z } from "zod";
import type { StepResult } from "@/lib/store";

const findingSchema = z.object({
  step: z.string(),
  severity: z.enum(["info", "warning", "error", "critical"]),
  message: z.string(),
  file: z.string().nullish(),
  line: z.number().int().nullish(),
  rule_id: z.string().nullish(),
  evidence: z.string().nullish(),
  suggestion: z.string().nullish(),
});

const stepResultSchema = z.object({
  step: z.string(),
  name: z.string(),
  passed: z.boolean(),
  findings: z.array(findingSchema).default([]),
  metrics: z.record(z.unknown()).optional(),
  skipped: z.boolean().optional(),
  skip_reason: z.string().nullish(),
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
  steps: z.array(stepResultSchema).default([]),
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
  return {
    ok: true,
    data: {
      passed: d.passed,
      pr_number: d.pr_number ?? null,
      commit_sha: d.commit_sha ?? null,
      repo: d.repo ?? null,
      steps: d.steps as StepResult[],
      summary: d.summary,
    },
  };
}
