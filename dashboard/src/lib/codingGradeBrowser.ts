/**
 * Browser-safe coding challenge helpers (no code execution).
 * Live execution was removed (RCE/XSS risk). Final grading is server-side only.
 */

export type CodingTestCase = {
  id?: string;
  args: unknown[];
  /** Present only on the server; never sent to the browser. */
  expected?: unknown;
  raises?: string;
  /** Client hint that a hidden expected value exists. */
  has_expected?: boolean;
};

export type CodingQuestionPublic = {
  id: string;
  entrypoint: string;
  tests: CodingTestCase[];
};

export type CodingGradeResult = {
  passed: boolean;
  passedTests: number;
  totalTests: number;
  errors: string[];
};

const ENTRYPOINT_RE = /^[A-Za-z_][A-Za-z0-9_]{0,64}$/;

/**
 * Structural preview only — does not execute user code in the browser.
 */
export function gradeCodingSubmissionBrowser(
  question: CodingQuestionPublic,
  source: string
): CodingGradeResult {
  const tests = question.tests ?? [];
  const totalTests = tests.length;
  if (!totalTests) {
    return { passed: false, passedTests: 0, totalTests: 0, errors: ["No tests"] };
  }
  if (!source?.trim()) {
    return {
      passed: false,
      passedTests: 0,
      totalTests,
      errors: ["Empty submission"],
    };
  }
  if (!ENTRYPOINT_RE.test(question.entrypoint || "")) {
    return {
      passed: false,
      passedTests: 0,
      totalTests,
      errors: ["Invalid entrypoint"],
    };
  }
  const name = question.entrypoint;
  const declared =
    new RegExp(
      String.raw`(?:function\s+${name}\s*\(|(?:const|let|var)\s+${name}\s*=)`,
    ).test(source) || source.includes(`${name} =`);

  if (!declared) {
    return {
      passed: false,
      passedTests: 0,
      totalTests,
      errors: [
        `Preview: declare function \`${name}\`. Full tests run on quiz submit (server).`,
      ],
    };
  }

  return {
    passed: false,
    passedTests: 0,
    totalTests,
    errors: [
      `Preview OK: \`${name}\` found. Submit the quiz for server-side grading (${totalTests} hidden tests).`,
    ],
  };
}
