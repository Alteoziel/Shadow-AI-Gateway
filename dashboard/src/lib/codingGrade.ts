/**
 * Grade interactive coding challenges with node:vm (no filesystem, short timeout).
 * Server-only — do not import from client components.
 */

import vm from "node:vm";
import type { CodingGradeResult, CodingTestCase } from "./codingGradeBrowser";

export type { CodingGradeResult, CodingTestCase };

export type CodingQuestion = {
  id: string;
  question_type?: string;
  entrypoint: string;
  starter_code?: string;
  tests: CodingTestCase[];
  language?: string;
};

function deepEqual(a: unknown, b: unknown): boolean {
  if (Object.is(a, b)) return true;
  return JSON.stringify(a) === JSON.stringify(b);
}

/**
 * Execute user source and run tests for one challenge.
 */
export function gradeCodingSubmission(
  question: CodingQuestion,
  source: string
): CodingGradeResult {
  const errors: string[] = [];
  const tests = question.tests ?? [];
  if (!tests.length) {
    return { passed: false, passedTests: 0, totalTests: 0, errors: ["No tests"] };
  }
  if (!source || !source.trim()) {
    return {
      passed: false,
      passedTests: 0,
      totalTests: tests.length,
      errors: ["Empty submission"],
    };
  }
  if (/require\s*\(|process\.|globalThis|Function\s*\(|child_process|fs\./.test(source)) {
    return {
      passed: false,
      passedTests: 0,
      totalTests: tests.length,
      errors: ["Source uses disallowed APIs"],
    };
  }

  let passedTests = 0;
  try {
    const context: Record<string, unknown> = {
      module: { exports: {} },
      exports: {},
      console: { log() {}, warn() {}, error() {} },
    };
    vm.createContext(context);
    const wrapped = `${source}\n;module.exports = typeof ${question.entrypoint} === "function" ? ${question.entrypoint} : null;`;
    vm.runInContext(wrapped, context, {
      timeout: 500,
      displayErrors: true,
    });
    const fn = (context.module as { exports: unknown }).exports;
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
            (fn as (...a: unknown[]) => unknown)(...(t.args ?? []));
          } catch (err) {
            threw = err;
          }
          const name =
            threw && typeof threw === "object" && "name" in threw
              ? String((threw as { name: string }).name)
              : threw
                ? "Error"
                : "";
          if (!threw) {
            errors.push(`${t.id ?? "test"}: expected throw ${t.raises}`);
          } else if (name !== t.raises && t.raises !== "Error") {
            errors.push(`${t.id ?? "test"}: threw ${name}, expected ${t.raises}`);
          } else {
            passedTests += 1;
          }
        } else {
          const got = (fn as (...a: unknown[]) => unknown)(...(t.args ?? []));
          if (!deepEqual(got, t.expected)) {
            errors.push(
              `${t.id ?? "test"}: expected ${JSON.stringify(t.expected)}, got ${JSON.stringify(got)}`
            );
          } else {
            passedTests += 1;
          }
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
