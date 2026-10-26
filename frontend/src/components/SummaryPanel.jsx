const money = (n) => n.toLocaleString(undefined, { style: "currency", currency: "USD" });

export default function SummaryPanel({ summary, onShowReview }) {
  if (!summary) return null;
  const entries = Object.entries(summary.by_category);
  return (
    <aside className="summary" aria-label="Totals">
      {summary.needs_review_count > 0 ? (
        <button className="review-count" onClick={onShowReview}>
          {summary.needs_review_count} {summary.needs_review_count === 1 ? "row needs" : "rows need"} your decision
        </button>
      ) : (
        <p className="all-clear">Every row is sorted.</p>
      )}
      <table>
        <caption>Spending by category</caption>
        <tbody>
          {entries.map(([name, total]) => (
            <tr key={name}>
              <th scope="row">{name}</th>
              <td className="num">{money(total)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th scope="row">Total spending</th>
            <td className="num">{money(summary.total_spending)}</td>
          </tr>
        </tfoot>
      </table>
      <dl className="side-notes">
        <dt>Refunds received</dt>
        <dd className="num">{money(summary.refunds)}</dd>
        <dt>Moved between accounts</dt>
        <dd className="num">{money(summary.not_spending)}</dd>
      </dl>
    </aside>
  );
}
