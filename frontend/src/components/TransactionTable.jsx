import ConfidenceBadge from './ConfidenceBadge.jsx'
import { money } from './SummaryCards.jsx'
import { CategorySelect } from './ReviewQueue.jsx'

const MAX_ROWS = 400

export default function TransactionTable({ rows, onAssign }) {
  const shown = rows.slice(0, MAX_ROWS)
  return (
    <section aria-label="All transactions">
      <h2>
        Every row, every decision{' '}
        <span className="hint-inline">
          (this is what the brain did, and why)
        </span>
      </h2>
      <div className="table-wrap">
        <table className="txn-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Description</th>
              <th className="num">Amount</th>
              <th>Confidence</th>
              <th>Category</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((t) => (
              <tr key={t.id} className={t.needs_review ? 'row-review' : ''}>
                <td className="date-cell">{t.date ?? t.date_raw}</td>
                <td>
                  <div className="desc">{t.description}</div>
                  <div className="norm" title="what the brain actually matched on">
                    {t.normalized}
                  </div>
                  {t.linked_category && (
                    <div className="linked">↩ offsets {t.linked_category}</div>
                  )}
                  {t.flags.length > 0 && (
                    <div className="flags">
                      {t.flags.map((f) => (
                        <span key={f} className="flag-chip">
                          {f.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  )}
                </td>
                <td className={`num ${t.amount > 0 ? 'pos' : 'neg'}`}>
                  {money(t.amount)}
                </td>
                <td>
                  <ConfidenceBadge band={t.band} confidence={t.confidence} />
                  <div className="reason" title={t.reasons.join(' · ')}>
                    {t.reasons[0]}
                  </div>
                </td>
                <td>
                  <CategorySelect row={t} onAssign={onAssign} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > MAX_ROWS && (
        <p className="hint">Showing first {MAX_ROWS} of {rows.length} rows.</p>
      )}
    </section>
  )
}
