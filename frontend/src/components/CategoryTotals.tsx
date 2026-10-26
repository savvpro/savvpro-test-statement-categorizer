import { formatCents } from "../lib/format";
import type { Summary } from "../types";

const KIND_LABEL = { income: "Income", expense: "Deductible", personal: "Not deductible" };

export function CategoryTotals({ summary }: { summary: Summary }) {
  const rows = summary.categories;
  return (
    <section className="panel" aria-labelledby="totals-title">
      <h2 id="totals-title">Totals by category</h2>
      {rows.length === 0 ? (
        <p className="muted">Nothing categorised yet.</p>
      ) : (
        <table className="totals">
          <thead>
            <tr>
              <th>Category</th>
              <th>Sch. C</th>
              <th className="num">Rows</th>
              <th className="num">Total</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.category} className={`kind-${c.kind}`}>
                <td>
                  <span className={`dot dot--${c.kind}`} aria-hidden />
                  {c.label}
                  <span className="muted small block">
                    {KIND_LABEL[c.kind as keyof typeof KIND_LABEL]}
                    {c.refund_cents > 0 && ` · ${formatCents(c.refund_cents)} refunded`}
                  </span>
                </td>
                <td className="muted">{c.schedule_c_line?.replace("Line ", "") ?? "—"}</td>
                <td className="num">{c.count}</td>
                <td className="num strong">{formatCents(c.total_cents)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {(summary.transfers_in_cents > 0 || summary.transfers_out_cents > 0) && (
        <p className="muted small">
          Transfers & card payments are left out of the totals: {formatCents(summary.transfers_in_cents)} in,{" "}
          {formatCents(summary.transfers_out_cents)} out.
        </p>
      )}
      <p className="muted small">
        Fuel and maintenance are only deductible if you use the actual-expense method instead of
        the standard mileage rate. Tolls and parking are deductible either way. This is not tax
        advice.
      </p>
    </section>
  );
}
