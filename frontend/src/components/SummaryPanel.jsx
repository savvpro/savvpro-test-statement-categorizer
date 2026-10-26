import { money } from "../format";

export default function SummaryPanel({ summary }) {
  return (
    <section className="card">
      <h2>Totals by category</h2>
      <div className="stats">
        <span>{summary.transaction_count} transactions</span>
        <span className={summary.needs_review_count ? "warn" : ""}>
          {summary.needs_review_count} need review
        </span>
        <span>{summary.duplicate_count} possible duplicates</span>
      </div>
      <table>
        <thead>
          <tr><th>Category</th><th className="num">Rows</th><th className="num">Total</th></tr>
        </thead>
        <tbody>
          {summary.totals.map((t) => (
            <tr key={t.category}>
              <td>{t.category}</td>
              <td className="num">{t.count}</td>
              <td className={`num ${Number(t.total) < 0 ? "neg" : "pos"}`}>{money(t.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}