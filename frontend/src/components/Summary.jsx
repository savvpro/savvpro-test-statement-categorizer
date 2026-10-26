import { formatMoney } from "../utils";

export default function Summary({ summary }) {
  const entries = Object.entries(summary.expenses);
  const pending = summary.needs_review_count;

  return (
    <section className="panel">
      <h2>Summary</h2>
      <div className="cards">
        <div className="card">
          <span className="label">Deductible total</span>
          <strong>{formatMoney(summary.deductible_total)}</strong>
        </div>
        <div className="card">
          <span className="label">Income</span>
          <strong>{formatMoney(summary.income)}</strong>
        </div>
        <div className={`card ${pending ? "warn" : ""}`}>
          <span className="label">Needs review</span>
          <strong>{pending} rows</strong>
          <span className="muted">{formatMoney(summary.needs_review_total)}</span>
        </div>
        <div className="card">
          <span className="label">Not spending</span>
          <strong>{summary.excluded_count} rows</strong>
          <span className="muted">transfers, card payments</span>
        </div>
      </div>

      {pending > 0 && (
        <p className="muted">
          Totals do not include the {pending} row(s) that need review. Fix them below.
        </p>
      )}

      {entries.length > 0 && (
        <table className="totals">
          <thead>
            <tr><th>Category</th><th className="num">Total</th></tr>
          </thead>
          <tbody>
            {entries.map(([name, total]) => (
              <tr key={name}>
                <td>{name}</td>
                <td className="num">{formatMoney(total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}