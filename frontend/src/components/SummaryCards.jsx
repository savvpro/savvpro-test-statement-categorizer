const fmt = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
})

export function money(n) {
  return fmt.format(n ?? 0)
}

export default function SummaryCards({ summary, meta }) {
  const cats = Object.entries(summary.by_category).sort((a, b) => b[1] - a[1])
  const max = Math.max(1, ...cats.map(([, v]) => v))

  return (
    <section aria-label="Summary">
      <div className="cards">
        <div className="card">
          <span className="card-label">Business spending</span>
          <span className="card-value">{money(summary.spending_total)}</span>
          <span className="card-sub">excludes transfers &amp; refunds</span>
        </div>
        <div className="card">
          <span className="card-label">Income in</span>
          <span className="card-value pos">{money(summary.income_total)}</span>
          <span className="card-sub">client payments &amp; payouts</span>
        </div>
        <div className="card">
          <span className="card-label">Refunds back</span>
          <span className="card-value pos">{money(summary.refunds_total)}</span>
          <span className="card-sub">money back — not income</span>
        </div>
        <div className="card">
          <span className="card-label">Needs review</span>
          <span className={`card-value ${summary.review_count ? 'warn' : ''}`}>
            {summary.review_count}
          </span>
          <span className="card-sub">of {summary.count} rows</span>
        </div>
      </div>

      <div className="card totals-card">
        <span className="card-label">Spending by category</span>
        {cats.length === 0 ? (
          <p className="hint">No spending rows categorized yet.</p>
        ) : (
          <ul className="totals-list">
            {cats.map(([name, value]) => (
              <li key={name}>
                <span className="totals-name">{name}</span>
                <span className="totals-bar-track">
                  <span
                    className="totals-bar"
                    style={{ width: `${Math.round((value / max) * 100)}%` }}
                  />
                </span>
                <span className="totals-value">{money(value)}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="hint">
          Transfers of {money(summary.transfers_total)} between your own accounts are
          excluded. {meta.rows_skipped > 0 && `${meta.rows_skipped} summary row(s) skipped.`}
        </p>
      </div>
    </section>
  )
}
