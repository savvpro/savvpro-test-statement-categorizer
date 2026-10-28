import Link from "next/link";
import { BRAND } from "@/lib/brand";

type Step = 1 | 2 | 3;
const STEPS = ["Upload", "Review", "Summary"];

export function TopBar({
  step,
  statementId,
  title,
}: {
  step: Step;
  statementId?: string;
  title?: React.ReactNode;
}) {
  const href = (i: number) =>
    i === 0 ? "/" : statementId ? (i === 1 ? `/statements/${statementId}` : `/statements/${statementId}/summary`) : null;
  return (
    <header className="border-b border-rule bg-row">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
        <Link href="/" className="text-lg font-semibold text-ink">
          {BRAND}
        </Link>
        {title ? <div className="min-w-0 flex-1 truncate text-muted">{title}</div> : <div className="flex-1" />}
        <nav aria-label="Progress">
          <ol className="flex items-center gap-2 text-sm">
            {STEPS.map((s, i) => {
              const n = i + 1;
              const target = href(i);
              const current = n === step;
              const inner = (
                <>
                  <span
                    className={`mr-1 inline-flex h-5 w-5 items-center justify-center rounded-full border text-xs ${
                      current ? "border-ledger bg-ledger text-white" : "border-rule text-muted"
                    }`}
                    aria-hidden="true"
                  >
                    {n}
                  </span>
                  {s}
                </>
              );
              return (
                <li key={s} className="flex items-center gap-2">
                  {i > 0 && <span className="h-px w-4 bg-rule" aria-hidden="true" />}
                  {target && !current ? (
                    <Link href={target} className="text-muted hover:text-ink">
                      {inner}
                    </Link>
                  ) : (
                    <span aria-current={current ? "step" : undefined} className={current ? "font-medium text-ink" : "text-muted"}>
                      {inner}
                    </span>
                  )}
                </li>
              );
            })}
          </ol>
        </nav>
      </div>
    </header>
  );
}
