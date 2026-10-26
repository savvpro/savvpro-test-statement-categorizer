import { formatMoney, getCategoryTone } from "../constants/categories";

const icon = {
  income: <path d="M12 19V5M5 12l7-7 7 7" />,
  expenses: <path d="M12 5v14M19 12l-7 7-7-7" />,
  refunds: <path d="M3 12a9 9 0 1 0 3-6.7M3 4v5h5" />,
  net: <path d="M4 7h16M4 12h16M4 17h10" />,
  review: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5M12 16h.01" />
    </>
  ),
};

function Stat({ tone, glyph, label, value, sub }) {
  return (
    <div className={"stat " + tone}>
      <span className="stat-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          {glyph}
        </svg>
      </span>
      <div>
        <span className="stat-label">{label}</span>
        <b className="stat-value">{value}</b>
        {sub && <span className="stat-sub">{sub}</span>}
      </div>
    </div>
  );
}

export default function CategorySummary({ summary, skipped }) {
  const fmt = formatMoney;
  const max = Math.max(1, ...summary.by_category.map((c) => Math.abs(c.total)));

  return (
    <section className="card">
      <div className="step-head">
        <span className="step">3</span>
        <div>
          <h2>Tax Totals by Category</h2>
          <p>
            Refunds are money back, not income. Categories marked No under &quot;Counted in
            totals?&quot; are left out of the totals.
          </p>
        </div>
      </div>

      <div className="stats">
        <Stat tone="teal" glyph={icon.income} label="Income" value={fmt(summary.income)} />
        <Stat tone="rose" glyph={icon.expenses} label="Expenses" value={fmt(summary.expenses)} />
        <Stat tone="sky" glyph={icon.refunds} label="Refunds" value={fmt(summary.refunds)} />
        <Stat tone="navy" glyph={icon.net} label="Net expenses" value={fmt(summary.net_expenses)} />
        <Stat
          tone={summary.needs_review_count ? "amber" : "teal"}
          glyph={icon.review}
          label="Needs review"
          value={summary.needs_review_count}
          sub={summary.needs_review_count === 1 ? "1 transaction" : `${summary.needs_review_count} transactions`}
        />
      </div>

      <div className="table-wrap">
        <table className="tx summary-table">
          <thead>
            <tr>
              <th>Category</th>
              <th>Rows</th>
              <th>Total</th>
              <th>Counted in totals?</th>
            </tr>
          </thead>
          <tbody>
            {summary.by_category.map((c) => {
              const tone = getCategoryTone(c.category);
              return (
                <tr key={c.category}>
                  <td>
                    <span className="cat-chip" style={{ background: tone.bg, color: tone.fg }}>
                      {c.category}
                    </span>
                  </td>
                  <td>{c.count}</td>
                  <td>
                    <div className="total-cell">
                      <span className="total-num">{fmt(c.total)}</span>
                      <span className="bar">
                        <i style={{ width: `${(Math.abs(c.total) / max) * 100}%`, background: tone.fg }} />
                      </span>
                    </div>
                  </td>
                  <td>
                    <span className={c.counted ? "yn yes" : "yn no"}>{c.counted ? "Yes" : "No"}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {skipped.length > 0 && (
        <div className="skipped">
          <h3>Skipped rows ({skipped.length}) · could not be read</h3>
          <ul>
            {skipped.map((s) => (
              <li key={s.row}>
                Line {s.row}: {s.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
