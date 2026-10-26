import { Download, PieChart } from "lucide-react";
import type { CategoryKind, Summary } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { Card, IconCircle, buttonSecondary, cx } from "./ui";

const barTone: Record<CategoryKind, string> = {
  spending: "bg-accent",
  refund: "bg-green",
  income: "bg-green",
  not_spending: "bg-line-strong",
  review: "bg-amber-line",
};

const kindLabel: Record<CategoryKind, string> = {
  spending: "Spending",
  refund: "Refund",
  income: "Income",
  not_spending: "Not spending",
  review: "Needs review",
};

export function CategoryTotals({ summary, exportUrl }: { summary: Summary; exportUrl: string }) {
  const { totals, categories } = summary;
  const max = Math.max(1, ...categories.map((c) => c.total));

  return (
    <Card>
      <div className="flex flex-wrap items-center gap-3 border-b border-line px-5 py-4">
        <IconCircle icon={PieChart} size="sm" />
        <div className="min-w-[12rem] flex-1">
          <h2 className="text-base font-semibold text-ink">Category totals</h2>
          <p className="text-xs text-muted">Needs Review rows are left out of every total until you categorize them.</p>
        </div>
        <a href={exportUrl} download className={`${buttonSecondary} w-full sm:w-auto`}>
          <Download size={16} strokeWidth={1.75} aria-hidden="true" />
          Export CSV
        </a>
      </div>

      <div className="grid gap-6 p-5 lg:grid-cols-[1fr_300px] lg:gap-8">
        {categories.length === 0 ? (
          <p className="text-sm text-muted">No categorized transactions yet.</p>
        ) : (
          <ul className="space-y-3.5">
            {categories.map((c) => (
              <li key={c.category}>
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="min-w-0 truncate text-ink">
                    {c.category}
                    <span className="ml-2 text-xs text-faint tabular-nums">
                      {c.count} {c.count === 1 ? "row" : "rows"}
                    </span>
                  </span>
                  <span
                    className={cx(
                      "shrink-0 font-medium tabular-nums",
                      c.kind === "refund" || c.kind === "income" ? "text-green" : "text-ink",
                    )}
                  >
                    {formatMoney(c.total)}
                  </span>
                </div>
                <div
                  className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-grey-soft"
                  role="img"
                  aria-label={`${kindLabel[c.kind]}: ${formatMoney(c.total)}`}
                >
                  <div
                    className={cx("h-full rounded-full", barTone[c.kind])}
                    style={{ width: `${(c.total / max) * 100}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}

        <dl className="space-y-2.5 rounded-lg border border-line bg-page p-4 text-sm lg:self-start">
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Spending</dt>
            <dd className="tabular-nums text-ink">{formatMoney(totals.spending)}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Refunds</dt>
            <dd className="tabular-nums text-green">
              {"\u2212"}
              {formatMoney(totals.refunds)}
            </dd>
          </div>
          <div className="flex justify-between gap-3 border-t border-line pt-2.5">
            <dt className="font-semibold text-ink">Net spending</dt>
            <dd className="font-semibold tabular-nums text-ink">{formatMoney(totals.net_spending)}</dd>
          </div>
          <div className="flex justify-between gap-3 pt-1 text-xs">
            <dt className="text-faint">Income (not deducted)</dt>
            <dd className="tabular-nums text-green">{formatMoney(totals.income)}</dd>
          </div>
          <div className="flex justify-between gap-3 text-xs">
            <dt className="text-faint">Transfers and card payments</dt>
            <dd className="tabular-nums text-faint">{formatMoney(totals.not_spending)}</dd>
          </div>
        </dl>
      </div>
    </Card>
  );
}
