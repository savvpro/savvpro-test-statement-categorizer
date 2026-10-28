import { Badge } from "@/components/ui/Badge";
import { money } from "@/lib/format";
import type { CategoryTotal } from "@/lib/types";

const KIND_LABEL: Record<CategoryTotal["kind"], string> = {
  income: "Income",
  expense: "Expense",
  refund: "Refund",
  not_spending: "Not spending",
  review: "Review",
};

export function CategoryTotals({ totals }: { totals: CategoryTotal[] }) {
  return (
    <div className="overflow-hidden rounded-2xl bg-white shadow-card ring-1 ring-brand-100">
      <div className="border-b border-brand-100 px-5 py-4">
        <h3 className="font-semibold text-brand-900">Totals by category</h3>
      </div>
      <ul className="divide-y divide-slate-100">
        {totals.map((t) => (
          <li key={t.category} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
            <div className="min-w-0">
              <p className="font-medium text-slate-800">{t.category}</p>
              <p className="text-xs text-slate-500">
                {KIND_LABEL[t.kind]} · {t.count} {t.count === 1 ? "row" : "rows"}
                {t.kind === "refund" && " · already subtracted from the purchase category"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {t.deductible && <Badge tone="green">Deductible</Badge>}
              <span className="font-semibold tabular-nums text-brand-900">{money(t.total)}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
