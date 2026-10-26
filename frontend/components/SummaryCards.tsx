import type { Summary } from "@/lib/api";
import { formatPkr, formatSignedPkr, netAmount } from "@/lib/format";

type Props = { summary: Summary; reviewActive: boolean; onReview: () => void };

export function SummaryCards({ summary, reviewActive, onReview }: Props) {
  const net = netAmount(summary.total_income, summary.total_spending);
  return (
    <section className="cards" aria-label="Summary">
      <div className="stat">
        <span className="stat-label">Income</span>
        <strong className="stat-value credit">{formatPkr(summary.total_income)}</strong>
      </div>
      <div className="stat">
        <span className="stat-label">Spending</span>
        <strong className="stat-value debit">{formatPkr(summary.total_spending)}</strong>
      </div>
      <div className="stat">
        <span className="stat-label">Net</span>
        <strong className={`stat-value ${net.startsWith("-") ? "debit" : "credit"}`}>{formatSignedPkr(net)}</strong>
      </div>
      <button type="button" className="stat stat-review" aria-pressed={reviewActive} onClick={onReview}>
        <span className="stat-label">Needs Review</span>
        <strong className="stat-value">{summary.needs_review_count}</strong>
        <span className="stat-hint">{reviewActive ? "Filter on" : "Show these rows"}</span>
      </button>
    </section>
  );
}
