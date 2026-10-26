import { money } from "../format.js";

export default function Summary({ summary }) {
  return (
    <section className="card">
      <h2>Summary</h2>
      <div className="stats">
        <Stat label="Business expenses" value={money(summary.business_expenses)} />
        <Stat label="Income" value={money(summary.income)} />
        <Stat label="Personal (not deductible)" value={money(summary.personal_spending)} />
        <Stat label="Transfers (excluded)" value={money(summary.transfers_excluded)} />
        <Stat
          label="Needs review"
          value={`${summary.needs_review_count} (${money(summary.needs_review_amount)})`}
          highlight={summary.needs_review_count > 0}
        />
      </div>
      {summary.expense_categories.length > 0 && (
        <table>
          <thead>
            <tr><th>Expense category</th><th className="num">Rows</th><th className="num">Net total</th></tr>
          </thead>
          <tbody>
            {summary.expense_categories.map((c) => (
              <tr key={c.category}>
                <td>{c.category}</td>
                <td className="num">{c.count}</td>
                <td className="num">{money(c.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="hint">Refunds are subtracted from their category and never counted as income.</p>
    </section>
  );
}

function Stat({ label, value, highlight }) {
  return (
    <div className={highlight ? "stat highlight" : "stat"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
