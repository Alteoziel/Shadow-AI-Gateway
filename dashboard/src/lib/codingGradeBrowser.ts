/**
 * Browser-safe coding challenge grading (no node:vm).
 * Server re-grades with codingGrade.ts on submit.
 */

export type CodingTestCase = {
  id?: string;
  args: unknown[];
  expected?: unknown;
  raises?: string;
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

export function gradeCodingSubmissionBrowser(
  question: CodingQuestionPublic,
  source: string
): CodingGradeResult {
  const errors: string[] = [];
  const tests = question.tests ?? [];
  if (!tests.length) {
    return { passed: false, passedTests: 0, totalTests: 0, errors: ["No tests"] };
  }
  if (!source?.trim()) {
    return {
      passed: false,
      passedTests: 0,
      totalTests: tests.length,
      errors: ["Empty submission"],
    };
  }
  let passedTests = 0;
  try {
    // eslint-disable-next-line no-new-func
    const factory = new Function(
      `${source}\n; return typeof ${question.entrypoint} === "function" ? ${question.entrypoint} : null;`
    );
    const fn = factory();
    if (typeof fn !== "function") {
      return {
        passed: false,
        passedTests: 0,
        totalTests: tests.length,
        errors: [`Missing function \`${question.entrypoint}\``],
      };
    }
    for (const t of tests) {
      try {
        if (t.raises) {
          let threw: unknown = null;
          try {
            fn(...(t.args ?? []));
          } catch (err) {
            threw = err;
          }
          const name =
            threw && typeof threw === "object" && "name" in threw
              ? String((threw as { name: string }).name)
              : threw
                ? "Error"
                : "";
          if (!threw) errors.push(`${t.id ?? "test"}: expected throw`);
          else if (name !== t.raises && t.raises !== "Error") {
            errors.push(`${t.id ?? "test"}: wrong error type`);
          } else passedTests += 1;
        } else {
          const got = fn(...(t.args ?? []));
          if (JSON.stringify(got) !== JSON.stringify(t.expected)) {
            errors.push(
              `${t.id ?? "test"}: expected ${JSON.stringify(t.expected)}, got ${JSON.stringify(got)}`
            );
          } else passedTests += 1;
        }
      } catch (err) {
        errors.push(
          `${t.id ?? "test"}: ${err instanceof Error ? err.message : String(err)}`
        );
      }
    }
  } catch (err) {
    errors.push(err instanceof Error ? err.message : String(err));
  }
  return {
    passed: passedTests === tests.length && tests.length > 0,
    passedTests,
    totalTests: tests.length,
    errors,
  };
}
