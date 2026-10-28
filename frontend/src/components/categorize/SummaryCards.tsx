import { money } from "@/lib/format";
import type { Summary } from "@/lib/types";

export function SummaryCards({ summary }: { summary: Summary }) {
  const cards = [
    { label: "Income", value: money(summary.income), hint: "Platform payouts, tips and bonuses", accent: "text-emerald-600" },
    { label: "Deductible expenses", value: money(summary.deductible_expenses), hint: "Net of refunds", accent: "text-brand-700" },
    { label: "Personal spending", value: money(summary.personal_spending), hint: "Not deductible", accent: "text-slate-700" },
    {
      label: "Needs review",
      value: String(summary.needs_review),
      hint: summary.needs_review ? "Rows waiting for you" : "All rows decided",
      accent: summary.needs_review ? "text-amber-600" : "text-emerald-600",
    },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((c) => (
        <div key={c.label} className="rounded-2xl bg-white p-5 shadow-card ring-1 ring-brand-100">
          <p className="text-sm font-medium text-slate-500">{c.label}</p>
          <p className={`mt-2 text-2xl font-bold ${c.accent}`}>{c.value}</p>
          <p className="mt-1 text-xs text-slate-500">{c.hint}</p>
        </div>
      ))}
    </div>
  );
}
