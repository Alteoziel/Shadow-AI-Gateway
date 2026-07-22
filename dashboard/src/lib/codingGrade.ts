/**
 * Grade interactive coding challenges without node:vm.
 *
 * User/source code runs only in a short-lived child process with a wiped
 * environment (no parent secrets). Entrypoint and source are statically
 * validated before any execution.
 *
 * Server-only — do not import from client components.
 */

import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
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

const MAX_TESTS = 32;

function deepEqual(a: unknown, b: unknown): boolean {
  if (Object.is(a, b)) return true;
  return JSON.stringify(a) === JSON.stringify(b);
}

const HARNESS = `"use strict";
const fs = require("fs");
const raw = fs.readFileSync(0, "utf8");
const { source, entrypoint, tests } = JSON.parse(raw);
const errors = [];
let passedTests = 0;
try {
  const module = { exports: {} };
  const exports = module.exports;
  const console = { log() {}, warn() {}, error() {} };
  // eslint-disable-next-line no-new-func
  const runner = new Function(
    "module",
    "exports",
    "console",
    source +
      ";\\nmodule.exports = typeof " +
      entrypoint +
      ' === "function" ? ' +
      entrypoint +
      " : null;"
  );
  runner(module, exports, console);
  const fn = module.exports;
  if (typeof fn !== "function") {
    process.stdout.write(
      JSON.stringify({
        passed: false,
        passedTests: 0,
        totalTests: tests.length,
        errors: ["Missing function \`" + entrypoint + "\`"],
      })
    );
    process.exit(0);
  }
  for (const t of tests) {
    try {
      if (t.raises) {
        let threw = null;
        try {
          fn(...(t.args || []));
        } catch (err) {
          threw = err;
        }
        const name =
          threw && typeof threw === "object" && threw.name
            ? String(threw.name)
            : threw
              ? "Error"
              : "";
        if (!threw) errors.push((t.id || "test") + ": expected throw " + t.raises);
        else if (name !== t.raises && t.raises !== "Error") {
          errors.push((t.id || "test") + ": threw " + name + ", expected " + t.raises);
        } else passedTests += 1;
      } else {
        const got = fn(...(t.args || []));
        if (JSON.stringify(got) !== JSON.stringify(t.expected)) {
          errors.push(
            (t.id || "test") +
              ": expected " +
              JSON.stringify(t.expected) +
              ", got " +
              JSON.stringify(got)
          );
        } else passedTests += 1;
      }
    } catch (err) {
      errors.push(
        (t.id || "test") + ": " + (err && err.message ? err.message : String(err))
      );
    }
  }
} catch (err) {
  errors.push(err && err.message ? err.message : String(err));
}
process.stdout.write(
  JSON.stringify({
    passed: passedTests === tests.length && tests.length > 0,
    passedTests,
    totalTests: tests.length,
    errors,
  })
);
`;

/**
 * Execute user source and run tests for one challenge in an isolated child.
 */
export function gradeCodingSubmission(
  question: CodingQuestion,
  source: string
): CodingGradeResult {
  const errors: string[] = [];
  const tests = (question.tests ?? []).slice(0, MAX_TESTS);
  if (!tests.length) {
    return { passed: false, passedTests: 0, totalTests: 0, errors: ["No tests"] };
  }

  const entrypoint = question.entrypoint || "solve";
  const entryErr = assertSafeEntrypoint(entrypoint);
  if (entryErr) {
    return {
      passed: false,
      passedTests: 0,
      totalTests: tests.length,
      errors: [entryErr],
    };
  }
  const sourceErr = assertSafeSource(source);
  if (sourceErr) {
    return {
      passed: false,
      passedTests: 0,
      totalTests: tests.length,
      errors: [sourceErr],
    };
  }

  let dir: string | null = null;
  try {
    dir = mkdtempSync(join(tmpdir(), "gov-code-grade-"));
    const scriptPath = join(dir, "harness.cjs");
    writeFileSync(scriptPath, HARNESS, "utf8");

    const payload = JSON.stringify({
      source,
      entrypoint,
      tests,
    });

    const result = spawnSync(process.execPath, [scriptPath], {
      input: payload,
      encoding: "utf8",
      timeout: 800,
      killSignal: "SIGKILL",
      // Wipe secrets from the parent environment.
      env: {
        PATH: process.env.PATH || "/usr/local/bin:/usr/bin:/bin",
        NODE_OPTIONS: "",
        HOME: dir,
        TMPDIR: dir,
      } as unknown as NodeJS.ProcessEnv,
      cwd: dir,
      maxBuffer: 256 * 1024,
    });

    if (result.error || result.status !== 0) {
      const msg =
        result.signal === "SIGKILL" || result.signal === "SIGTERM"
          ? "Grading timed out"
          : (typeof result.stderr === "string" ? result.stderr : "").slice(0, 200) ||
            result.error?.message ||
            "Grading process failed";
      return {
        passed: false,
        passedTests: 0,
        totalTests: tests.length,
        errors: [msg],
      };
    }

    const stdout =
      typeof result.stdout === "string" ? result.stdout : String(result.stdout || "");
    const parsed = JSON.parse(stdout.trim() || "{}") as CodingGradeResult;
    if (
      typeof parsed.passed !== "boolean" ||
      typeof parsed.passedTests !== "number" ||
      typeof parsed.totalTests !== "number"
    ) {
      return {
        passed: false,
        passedTests: 0,
        totalTests: tests.length,
        errors: ["Invalid grader output"],
      };
    }
    return {
      passed: parsed.passed,
      passedTests: parsed.passedTests,
      totalTests: parsed.totalTests,
      errors: Array.isArray(parsed.errors)
        ? parsed.errors.map(String).slice(0, 20)
        : [],
    };
  } catch (err) {
    errors.push(err instanceof Error ? err.message : String(err));
    return {
      passed: false,
      passedTests: 0,
      totalTests: tests.length,
      errors,
    };
  } finally {
    if (dir) {
      try {
        rmSync(dir, { recursive: true, force: true });
      } catch {
        /* ignore cleanup errors */
      }
    }
  }
}

/** Used by unit-style checks without spawning (expected equality helper). */
export function _deepEqualForTests(a: unknown, b: unknown): boolean {
  return deepEqual(a, b);
}
