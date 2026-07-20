"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Review, StepResult } from "@/lib/store";
import { MiniCodeEditor } from "@/components/MiniCodeEditor";
import {
  gradeCodingSubmissionBrowser,
  type CodingGradeResult,
} from "@/lib/codingGradeBrowser";

/**
 * Keep the reviewer secret in process memory only — never sessionStorage /
 * localStorage (CodeQL js/clear-text-storage-of-sensitive-data).
 * Cleared on full page reload; user re-enters via Unlock.
 */
let reviewerSecretMemory = "";

function getReviewerSecret(): string {
  if (typeof window === "undefined") return "";
  return reviewerSecretMemory;
}

function setReviewerSecret(value: string) {
  reviewerSecretMemory = value;
}

function clearReviewerSecret() {
  reviewerSecretMemory = "";
}

function ensureReviewerSecret(): string | null {
  let secret = getReviewerSecret();
  if (!secret) {
    secret =
      window.prompt(
        "Enter reviewer secret (GOVERNANCE_DASHBOARD_SECRET or GOVERNANCE_REVIEWER_SECRET):"
      ) || "";
    if (!secret) return null;
    setReviewerSecret(secret);
  }
  return secret;
}

function authHeaders(): HeadersInit {
  const secret = getReviewerSecret();
  return {
    "Content-Type": "application/json",
    ...(secret ? { "X-Governance-Reviewer-Secret": secret } : {}),
  };
}

function statusColor(status: Review["status"]) {
  switch (status) {
    case "merged":
    case "approved":
      return "text-signal";
    case "rejected":
      return "text-alert";
    case "pending_comprehension":
      return "text-warn";
    default:
      return "text-warn";
  }
}

function StepCard({ step }: { step: StepResult }) {
  const profiles = (step.metrics?.profiles ?? null) as Record<
    string,
    { sizes: number[]; times_ms: number[]; estimated: string }
  > | null;

  const chartData =
    profiles &&
    Object.entries(profiles).flatMap(([name, p]) =>
      p.sizes.map((size, i) => ({
        name: `${name}@${size}`,
        algo: name,
        size,
        ms: p.times_ms[i],
      }))
    );

  return (
    <section className="border-b border-white/10 py-6 last:border-0">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-display text-xl text-white">{step.name}</h3>
        <span
          className={`text-sm font-semibold uppercase tracking-wide ${
            step.skipped ? "text-mist" : step.passed ? "text-signal" : "text-alert"
          }`}
        >
          {step.skipped ? "skipped" : step.passed ? "pass" : "fail"}
        </span>
      </div>

      {step.findings.length === 0 ? (
        <p className="text-sm text-mist">No findings.</p>
      ) : (
        <ul className="space-y-2">
          {step.findings.map((f, i) => (
            <li
              key={`${f.rule_id}-${i}`}
              className="rounded-md bg-black/25 px-3 py-2 text-sm"
            >
              <span className="font-semibold uppercase text-mist">
                {f.severity}
              </span>
              {f.file ? (
                <span className="text-mist">
                  {" "}
                  · {f.file}
                  {f.line ? `:${f.line}` : ""}
                </span>
              ) : null}
              <p className="mt-1 text-white/90">{f.message}</p>
              {f.suggestion ? (
                <p className="mt-1 text-mist">{f.suggestion}</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {chartData && chartData.length > 0 ? (
        <div className="mt-5 h-56 w-full">
          <p className="mb-2 text-xs uppercase tracking-wider text-mist">
            Big-O timing curves (ms)
          </p>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff22" />
              <XAxis dataKey="name" tick={{ fill: "#9aa8c0", fontSize: 10 }} />
              <YAxis tick={{ fill: "#9aa8c0", fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  background: "#141c2e",
                  border: "1px solid #ffffff22",
                }}
              />
              <Bar dataKey="ms" fill="#3d9a7a" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : null}
    </section>
  );
}

type PublicQuestion = {
  id: string;
  category: string;
  category_label?: string;
  prompt: string;
  choices: string[];
  format?: "text" | "code";
  question_type?: string;
  language?: string;
  starter_code?: string;
  entrypoint?: string;
  tests?: {
    id?: string;
    args: unknown[];
    expected?: unknown;
    raises?: string;
  }[];
};

type CodingDraft = {
  code: string;
  result: CodingGradeResult | null;
  running: boolean;
};

function renderQuizPrompt(prompt: string) {
  const parts = prompt.split(/(```[\s\S]*?```)/g);
  return parts.map((part, i) => {
    if (part.startsWith("```")) {
      const body = part.replace(/^```(?:\w+)?\n?/, "").replace(/```$/, "");
      return (
        <pre
          key={i}
          className="mt-2 overflow-x-auto rounded-md bg-black/50 p-3 text-xs leading-relaxed text-signal"
        >
          <code>{body}</code>
        </pre>
      );
    }
    return (
      <span
        key={i}
        dangerouslySetInnerHTML={{
          __html: part.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>"),
        }}
      />
    );
  });
}

function ReviewerUnlock() {
  const [hasSecret, setHasSecret] = useState(false);

  useEffect(() => {
    setHasSecret(Boolean(getReviewerSecret()));
  }, []);

  return (
    <div className="mb-4 rounded-md border border-white/10 bg-black/25 px-3 py-3 text-sm text-mist">
      {hasSecret ? (
        <div className="space-y-1">
          <p className="font-semibold text-signal">
            Review actions unlocked for this browser session.
          </p>
          <p>
            Quiz, approve, reject, and merge calls send{" "}
            <code>X-Governance-Reviewer-Secret</code>. If a request returns 401,
            clear the saved secret and unlock again.
          </p>
          <button
            type="button"
            className="text-signal underline"
            onClick={() => {
              clearReviewerSecret();
              setHasSecret(false);
            }}
          >
            Clear saved reviewer secret
          </button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-semibold text-warn">Review actions locked.</p>
            <p>
              Enter <code>GOVERNANCE_REVIEWER_SECRET</code> or the dashboard
              secret to submit the quiz, approve, reject, or merge.
            </p>
          </div>
          <button
            type="button"
            className="rounded-md bg-white/10 px-3 py-1 text-white hover:bg-white/20"
            onClick={() => {
              const s = ensureReviewerSecret();
              setHasSecret(Boolean(s));
            }}
          >
            Unlock actions
          </button>
        </div>
      )}
    </div>
  );
}

function ComprehensionPanel({ review }: { review: Review }) {
  const pack = review.comprehension;
  const questions = (pack?.questions ?? []) as PublicQuestion[];
  const codingQuestions = useMemo(
    () => questions.filter((q) => q.question_type === "coding"),
    [questions]
  );
  const mcQuestions = useMemo(
    () => questions.filter((q) => q.question_type !== "coding"),
    [questions]
  );
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [codingDrafts, setCodingDrafts] = useState<Record<string, CodingDraft>>(
    () => {
      const initial: Record<string, CodingDraft> = {};
      for (const q of questions) {
        if (q.question_type === "coding") {
          initial[q.id] = {
            code: q.starter_code || "",
            result: null,
            running: false,
          };
        }
      }
      return initial;
    }
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [explanations, setExplanations] = useState<
    {
      id: string;
      correct: boolean;
      explanation: string;
      coding?: CodingGradeResult | null;
    }[] | null
  >(null);

  const allMcAnswered = useMemo(
    () => mcQuestions.every((q) => answers[q.id] !== undefined),
    [answers, mcQuestions]
  );
  const allCodingPassed = useMemo(
    () =>
      codingQuestions.every((q) => codingDrafts[q.id]?.result?.passed === true),
    [codingDrafts, codingQuestions]
  );
  const canSubmit =
    questions.length > 0 && allMcAnswered && allCodingPassed && !busy;

  function runCodingTests(q: PublicQuestion) {
    if (!q.entrypoint || !q.tests?.length) return;
    const draft = codingDrafts[q.id];
    const code = draft?.code ?? q.starter_code ?? "";
    setCodingDrafts((prev) => ({
      ...prev,
      [q.id]: { code, result: prev[q.id]?.result ?? null, running: true },
    }));
    const result = gradeCodingSubmissionBrowser(
      { id: q.id, entrypoint: q.entrypoint, tests: q.tests },
      code
    );
    setCodingDrafts((prev) => ({
      ...prev,
      [q.id]: { code, result, running: false },
    }));
  }

  if (!pack) {
    return (
      <section className="mb-8 rounded-lg border border-dashed border-white/15 p-5 text-sm text-mist">
        No comprehension quiz attached yet. Re-run the guardrail suite so Step 6
        can generate a beginner study guide + quiz for this PR. Approve/Merge stay
        locked until a quiz exists and is passed.
      </section>
    );
  }

  if (review.comprehension_passed) {
    const attempt = review.comprehension_attempt;
    return (
      <section className="mb-8 rounded-lg bg-signal/10 p-5">
        <p className="text-xs uppercase tracking-[0.2em] text-signal">
          Step 6 · Comprehension passed
        </p>
        <p className="mt-2 text-white">
          You scored{" "}
          {attempt
            ? `${attempt.correct}/${attempt.total} (${Math.round(attempt.score * 100)}%)`
            : "a passing mark"}
          . Step 7 approve/merge is unlocked (suite must also be green to merge).
        </p>
      </section>
    );
  }

  async function submit() {
    if (!ensureReviewerSecret()) {
      setMessage("Reviewer secret required to submit the quiz.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const coding_submissions = Object.fromEntries(
        codingQuestions.map((q) => [
          q.id,
          codingDrafts[q.id]?.code ?? q.starter_code ?? "",
        ])
      );
      const res = await fetch(`/api/reviews/${review.id}`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          action: "submit_quiz",
          answers,
          coding_submissions,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 401) {
          clearReviewerSecret();
        }
        setMessage(data.message || data.error || "Quiz submit failed");
        return;
      }
      setExplanations(data.explanations ?? null);
      if (data.attempt?.passed) {
        window.location.reload();
        return;
      }
      setMessage(
        `Not yet — ${data.attempt.correct}/${data.attempt.total} ` +
          `(need ≥ ${Math.round((data.attempt.threshold ?? 0.8) * 100)}%). ` +
          `Re-read the study guide and try again.`
      );
    } finally {
      setBusy(false);
    }
  }

  const guide = pack.study_guide;

  return (
    <section className="mb-8 rounded-xl border border-warn/30 bg-black/20 p-5">
      <p className="text-xs uppercase tracking-[0.2em] text-warn">
        Step 6 · Comprehension Gate
      </p>
      <h3 className="mt-2 font-display text-2xl text-white">
        Prove you understand this change
      </h3>
      <p className="mt-2 max-w-3xl text-sm text-mist">
        You are learning — that is expected. Merging AI-written code you cannot
        explain is the danger. Read the guide, then pass the quiz (≥{" "}
        {Math.round((pack.pass_threshold ?? 0.8) * 100)}%) before Approve &amp; Merge
        unlocks.
      </p>

      <div className="mt-6 space-y-5 text-sm">
        <div>
          <h4 className="font-semibold text-white">What changed (plain English)</h4>
          <p className="mt-1 text-white/85">{guide.elevator_pitch}</p>
        </div>
        <div>
          <h4 className="font-semibold text-white">Bigger picture</h4>
          <p className="mt-1 text-white/85">{guide.bigger_picture}</p>
        </div>
        <div>
          <h4 className="font-semibold text-white">Vocabulary</h4>
          <ul className="mt-2 space-y-2">
            {guide.glossary.map((g) => (
              <li key={g.term} className="rounded-md bg-black/30 px-3 py-2">
                <span className="text-signal">{g.term}</span>
                <span className="text-mist"> — {g.definition}</span>
              </li>
            ))}
          </ul>
        </div>
        {guide.key_functions?.length ? (
          <div>
            <h4 className="font-semibold text-white">Key functions</h4>
            <ul className="mt-2 space-y-2">
              {guide.key_functions.map((fn) => (
                <li
                  key={`${fn.file}-${fn.name}`}
                  className="rounded-md bg-black/30 px-3 py-2"
                >
                  <code className="text-white">{fn.name}</code>
                  <span className="text-mist"> · {fn.file}</span>
                  <p className="mt-1 text-white/80">{fn.plain_english}</p>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <div>
          <h4 className="font-semibold text-white">Dependencies</h4>
          <p className="mt-1 text-mist">{guide.dependencies.join(", ")}</p>
        </div>
        <div>
          <h4 className="font-semibold text-white">Manual things you may need to do</h4>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-white/85">
            {guide.manual_dev_tasks.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-white">Security</h4>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-white/85">
            {guide.security_notes.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-8 space-y-6 border-t border-white/10 pt-6">
        <h4 className="font-display text-xl text-white">Quiz</h4>
        <p className="text-sm text-mist">
          Multiple-choice questions plus short coding challenges in a mini editor.
          Run the tests on each challenge until they pass, then submit.
        </p>
        {questions.map((q, i) => {
          const isCoding = q.question_type === "coding";
          const draft = codingDrafts[q.id] ?? {
            code: q.starter_code || "",
            result: null,
            running: false,
          };
          const explanation = explanations?.find((e) => e.id === q.id);
          return (
            <fieldset key={q.id} className="space-y-2">
              <legend className="text-sm text-white">
                <span className="text-mist">
                  {i + 1}. [{q.category_label || q.category}]
                  {isCoding ? " · write code" : ""}
                </span>{" "}
                <span className="mt-1 block whitespace-pre-wrap">
                  {renderQuizPrompt(q.prompt)}
                </span>
              </legend>
              {isCoding ? (
                <div className="space-y-2">
                  <MiniCodeEditor
                    value={draft.code}
                    running={draft.running}
                    onChange={(code) =>
                      setCodingDrafts((prev) => ({
                        ...prev,
                        [q.id]: { code, result: null, running: false },
                      }))
                    }
                    onReset={() =>
                      setCodingDrafts((prev) => ({
                        ...prev,
                        [q.id]: {
                          code: q.starter_code || "",
                          result: null,
                          running: false,
                        },
                      }))
                    }
                    onRun={() => runCodingTests(q)}
                  />
                  {draft.result ? (
                    <p
                      className={`text-xs ${
                        draft.result.passed ? "text-signal" : "text-alert"
                      }`}
                    >
                      {draft.result.passed
                        ? `All ${draft.result.totalTests} tests passed.`
                        : `${draft.result.passedTests}/${draft.result.totalTests} tests passed. ${draft.result.errors[0] ?? ""}`}
                    </p>
                  ) : (
                    <p className="text-xs text-mist">
                      Click “Run tests” — all must pass before you can submit.
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-1">
                  {q.choices.map((choice, idx) => (
                    <label
                      key={idx}
                      className={`flex cursor-pointer gap-2 rounded-md px-3 py-2 text-sm ${
                        answers[q.id] === idx
                          ? "bg-signal/20 text-white"
                          : "bg-black/25 text-white/85"
                      }`}
                    >
                      <input
                        type="radio"
                        className="mt-1"
                        name={q.id}
                        checked={answers[q.id] === idx}
                        onChange={() =>
                          setAnswers((prev) => ({ ...prev, [q.id]: idx }))
                        }
                      />
                      <span>{choice}</span>
                    </label>
                  ))}
                </div>
              )}
              {explanation ? (
                <p
                  className={`text-xs ${
                    explanation.correct ? "text-signal" : "text-alert"
                  }`}
                >
                  {explanation.explanation}
                  {explanation.coding && !explanation.coding.passed
                    ? ` (${explanation.coding.errors[0] ?? "tests failed"})`
                    : ""}
                </p>
              ) : null}
            </fieldset>
          );
        })}

        <button
          type="button"
          disabled={!canSubmit}
          onClick={submit}
          className="rounded-md bg-warn px-4 py-2 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy
            ? "Grading…"
            : !allCodingPassed
              ? "Pass all coding challenges first"
              : !allMcAnswered
                ? "Answer all multiple-choice questions"
                : "Submit comprehension quiz"}
        </button>
        {message ? <p className="text-sm text-alert">{message}</p> : null}
      </div>
    </section>
  );
}

export function ReviewActions({ review }: { review: Review }) {
  async function act(action: "approve" | "reject" | "merge") {
    if (!ensureReviewerSecret()) {
      alert("Reviewer secret required.");
      return;
    }
    const note =
      action === "reject"
        ? window.prompt("Rejection note (optional):") ?? ""
        : action === "merge"
          ? window.prompt(
              "Merge confirmation note (optional). This calls GitHub merge API:"
            ) ?? ""
          : "";
    const res = await fetch(`/api/reviews/${review.id}`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ action, note }),
    });
    const data = await res.json();
    if (!res.ok) {
      if (res.status === 401) {
        clearReviewerSecret();
      }
      alert(data.message || data.error || "Action failed");
      return;
    }
    window.location.reload();
  }

  const quizLocked = !review.comprehension || !review.comprehension_passed;
  const mergeLocked = quizLocked || !review.passed;

  return (
    <div className="mt-6 flex flex-wrap gap-3">
      <button
        type="button"
        disabled={quizLocked}
        onClick={() => act("approve")}
        className="rounded-md bg-signal px-4 py-2 text-sm font-semibold text-ink transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Approve
      </button>
      <button
        type="button"
        onClick={() => act("reject")}
        className="rounded-md border border-alert/60 px-4 py-2 text-sm font-semibold text-alert transition hover:bg-alert/10"
      >
        Reject
      </button>
      <button
        type="button"
        disabled={mergeLocked}
        onClick={() => act("merge")}
        className="rounded-md bg-white px-4 py-2 text-sm font-semibold text-ink transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Approve &amp; Merge
      </button>
      <p className={`w-full text-sm ${statusColor(review.status)}`}>
        Status: {review.status.replaceAll("_", " ")}
        {!review.comprehension_passed
          ? " · complete Step 6 quiz to unlock"
          : !review.passed
            ? " · suite failed — merge blocked"
            : ""}
      </p>
    </div>
  );
}

export function ReviewDetail({ review }: { review: Review }) {
  return (
    <article className="rounded-xl bg-slatepanel/80 p-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
      <header className="mb-4 border-b border-white/10 pb-4">
        <p className="text-xs uppercase tracking-[0.2em] text-mist">
          Human Review Panel · Step 7
        </p>
        <h2 className="mt-2 font-display text-3xl text-white">
          {review.repo ? `${review.repo}` : "Local review"}
          {review.pr_number ? ` · PR #${review.pr_number}` : ""}
        </h2>
        <p className="mt-2 text-sm text-mist">
          Suite:{" "}
          {review.passed ? "passed automated gates" : "failed automated gates"} ·{" "}
          {String(review.summary?.blocking_findings ?? 0)} blocking · commit{" "}
          <code className="text-white/80">
            {review.commit_sha?.slice(0, 8) ?? "n/a"}
          </code>
        </p>
        <ReviewerUnlock />
        <ReviewActions review={review} />
      </header>

      <ComprehensionPanel review={review} />

      {review.steps.map((step) => (
        <StepCard key={step.step} step={step} />
      ))}
    </article>
  );
}
