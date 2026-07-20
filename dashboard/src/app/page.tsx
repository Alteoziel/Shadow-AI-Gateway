import Link from "next/link";
import {
  getReview,
  getStoreStatus,
  listReviews,
  sanitizeReviewForClient,
  type Review,
} from "@/lib/store";
import { ReviewDetail } from "@/components/ReviewPanel";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type Props = {
  searchParams: Promise<{ id?: string }>;
};

export default async function HomePage({ searchParams }: Props) {
  let id: string | undefined;
  try {
    ({ id } = await searchParams);
  } catch {
    id = undefined;
  }

  let reviews: Review[] = [];
  let selected: Review | null = null;
  let loadError: string | null = null;
  const storeStatus = getStoreStatus();

  try {
    reviews = await listReviews();
    const selectedRaw = id ? await getReview(id) : reviews[0] ?? null;
    selected = selectedRaw ? sanitizeReviewForClient(selectedRaw) : null;
  } catch (err) {
    loadError = err instanceof Error ? err.message : "Store unavailable";
    console.error("[governance-dashboard] page load failed", err);
  }

  const banner = loadError || storeStatus.warning;

  return (
    <main>
      <header className="mb-10">
        <p className="text-xs uppercase tracking-[0.25em] text-mist">
          Shadow AI Gateway
        </p>
        <h1 className="mt-3 font-display text-5xl leading-tight text-white md:text-6xl">
          Governance
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-mist">
          Pass the beginner comprehension quiz, then review AST, OWASP, fuzz,
          Big-O, and copyright reports before merging to{" "}
          <code className="text-white/80">main</code>.
        </p>
      </header>

      {banner ? (
        <div
          className="mb-8 rounded-xl border border-warn/40 bg-warn/10 p-6 text-sm text-mist"
          role="alert"
        >
          <p className="font-semibold text-warn">Dashboard store notice</p>
          <p className="mt-2">{banner}</p>
          <p className="mt-3">
            Vercel project → Storage → create Upstash Redis → connect to this
            project → ensure env vars apply to Production and Preview →
            Redeploy. Also set{" "}
            <code className="text-white/80">GOVERNANCE_DASHBOARD_SECRET</code>.
          </p>
        </div>
      ) : null}

      <div className="grid gap-8 lg:grid-cols-[280px_1fr]">
        <aside className="space-y-3">
          <h2 className="text-xs uppercase tracking-[0.2em] text-mist">
            Pending &amp; recent
          </h2>
          {reviews.length === 0 ? (
            <p className="text-sm text-mist">
              No reviews yet. CI will POST here when{" "}
              <code>GOVERNANCE_DASHBOARD_URL</code> is set to this deployment
              URL and <code>GOVERNANCE_DASHBOARD_SECRET</code> matches the
              Vercel env var exactly. A 401 in the Actions log means the
              secrets do not match — fix them, then re-run{" "}
              <strong className="font-semibold text-white">
                Governance Steps 1–6
              </strong>
              .
            </p>
          ) : (
            <ul className="space-y-2">
              {reviews.map((r) => (
                <li key={r.id}>
                  <Link
                    href={`/?id=${r.id}`}
                    className={`block rounded-lg px-3 py-3 text-sm transition ${
                      selected?.id === r.id
                        ? "bg-slatepanel ring-1 ring-signal/40"
                        : "bg-slatepanel/70 hover:bg-slatepanel"
                    }`}
                  >
                    <span className="font-semibold text-white">
                      {r.repo ?? "local"}
                      {r.pr_number ? ` #${r.pr_number}` : ""}
                    </span>
                    <span className="mt-1 block text-xs text-mist">
                      {r.status.replaceAll("_", " ")} ·{" "}
                      {r.comprehension_passed ? "quiz done" : "quiz pending"} ·{" "}
                      {r.passed ? "suite pass" : "suite fail"}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <div>
          {selected ? (
            <ReviewDetail review={selected as Review} />
          ) : (
            <div className="rounded-xl border border-dashed border-white/15 p-10 text-mist">
              Waiting for the first guardrail report from GitHub Actions.
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
