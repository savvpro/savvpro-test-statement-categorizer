import { MANUAL_CATEGORIES, money } from "../format";

export default function ReviewPanel({ transactions, onCorrect, busy }) {
  const rows = transactions.filter((t) => t.needs_review);

  if (rows.length === 0) {
    return (
      <section className="card">
        <h2>Needs review</h2>
        <p className="ok">Nothing to review. Every row was categorized with confidence.</p>
      </section>
    );
  }

  return (
    <section className="card review">
      <h2>Needs review ({rows.length})</h2>
      <p className="hint">
        Pick a category once and every row with the same description is fixed too.
      </p>
      {rows.map((t) => (
        <div className="review-row" key={t.id}>
          <div className="review-main">
            <strong>{t.description}</strong>
            <span>{t.date} · {money(t.amount)}</span>
            <small>{t.explanation}</small>
          </div>
          <select
            disabled={busy}
            value=""
            onChange={(e) => e.target.value && onCorrect(t.id, e.target.value)}
          >
            <option value="">Choose category…</option>
            {MANUAL_CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      ))}
    </section>
  );
}