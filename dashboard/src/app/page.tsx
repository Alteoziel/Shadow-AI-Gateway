import Link from "next/link";
import { getReview, listReviews } from "@/lib/store";
import { ReviewDetail } from "@/components/ReviewPanel";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{ id?: string }>;
};

export default async function HomePage({ searchParams }: Props) {
  const { id } = await searchParams;
  const reviews = await listReviews();
  const selected = id ? await getReview(id) : reviews[0] ?? null;

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
          Engineering managers review AST, OWASP, fuzz, Big-O, and copyright
          reports before merging to <code className="text-white/80">main</code>.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-[280px_1fr]">
        <aside className="space-y-3">
          <h2 className="text-xs uppercase tracking-[0.2em] text-mist">
            Pending &amp; recent
          </h2>
          {reviews.length === 0 ? (
            <p className="text-sm text-mist">
              No reviews yet. CI will POST here when{" "}
              <code>GOVERNANCE_DASHBOARD_URL</code> is set.
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
                      {r.status} · {r.passed ? "suite pass" : "suite fail"}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <div>
          {selected ? (
            <ReviewDetail review={selected} />
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
