/**
 * Coding challenge helpers — NO code execution.
 *
 * Prior denylist + child_process / new Function approaches are not a sandbox
 * (constructor-split escapes can reach process.getBuiltinModule / fs).
 * Structural checks only; coding items do not auto-pass the quiz.
 *
 * Server-only — do not import from client components.
 */

import type { CodingGradeResult, CodingTestCase } from "./codingGradeBrowser";
import {
  assertSafeEntrypoint,
  assertSafeSource,
  MAX_SOURCE_BYTES,
} from "./codingSafety";

export type { CodingGradeResult, CodingTestCase };
export { assertSafeEntrypoint, assertSafeSource, MAX_SOURCE_BYTES };

export type CodingQuestion = {
  id: string;
  question_type?: string;
  entrypoint: string;
  starter_code?: string;
  tests: CodingTestCase[];
  language?: string;
};

/**
 * Structural validation only. Never executes user source.
 * Returns passed=false so coding cannot open an RCE path via auto-grade.
 */
export function gradeCodingSubmission(
  question: CodingQuestion,
  source: string
): CodingGradeResult {
  const tests = question.tests ?? [];
  const totalTests = tests.length;
  const errors: string[] = [];

  const entrypoint = question.entrypoint || "solve";
  const entryErr = assertSafeEntrypoint(entrypoint);
  if (entryErr) {
    return { passed: false, passedTests: 0, totalTests, errors: [entryErr] };
  }
  const sourceErr = assertSafeSource(source);
  if (sourceErr) {
    return { passed: false, passedTests: 0, totalTests, errors: [sourceErr] };
  }

  const declared = new RegExp(
    String.raw`(?:function\s+${entrypoint}\s*\(|(?:const|let|var)\s+${entrypoint}\s*=|\b${entrypoint}\s*=\s*(?:async\s*)?\()`
  ).test(source);
  if (!declared) {
    errors.push(`Declare \`${entrypoint}\` (function or const).`);
  } else {
    errors.push(
      "Coding execution is disabled on the server (security). " +
        "Multiple-choice answers determine the quiz pass; a reviewer should spot-check coding."
    );
  }

  return {
    passed: false,
    passedTests: 0,
    totalTests,
    errors,
  };
}
