import { formatCents } from "../lib/format";
import type { Summary } from "../types";

export function SummaryCards({ summary }: { summary: Summary }) {
  const provisional = summary.needs_review_count > 0;
  return (
    <div className="cards">
      <div className="card">
        <span className="card__label">Gig income</span>
        <span className="card__value">{formatCents(summary.income_cents)}</span>
        <span className="card__hint">Schedule C line 1</span>
      </div>
      <div className="card">
        <span className="card__label">Deductible expenses</span>
        <span className="card__value">{formatCents(summary.deductible_expenses_cents)}</span>
        <span className="card__hint">after refunds</span>
      </div>
      <div className="card">
        <span className="card__label">Estimated net profit</span>
        <span className="card__value">{formatCents(summary.net_profit_cents)}</span>
        <span className="card__hint">{provisional ? "provisional" : "income − expenses"}</span>
      </div>
      <div className={`card${provisional ? " card--warn" : " card--ok"}`}>
        <span className="card__label">Needs review</span>
        <span className="card__value">{summary.needs_review_count}</span>
        <span className="card__hint">
          {provisional
            ? `${formatCents(summary.needs_review_cents)} not in any total yet`
            : "everything is sorted"}
        </span>
      </div>
    </div>
  );
}
