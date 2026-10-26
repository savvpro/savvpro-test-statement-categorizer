import ConfidenceBadge from './ConfidenceBadge.jsx'
import { money } from './SummaryCards.jsx'

/** Rows the brain is unsure about. One click resolves each. */
export default function ReviewQueue({ rows, onAssign }) {
  if (rows.length === 0) {
    return (
      <div className="banner banner-ok">
        ✅ Nothing needs review — the brain was confident about every row.
      </div>
    )
  }

  return (
    <section aria-label="Needs review" className="review-queue">
      <h2>
        Needs review <span className="count-chip">{rows.length}</span>
      </h2>
      <p className="hint">
        The brain would rather ask than guess. Assign a category and totals update
        instantly.
      </p>
      <ul className="review-list">
        {rows.map((t) => (
          <li key={t.id} className="review-row">
            <div className="review-info">
              <span className="review-desc">{t.description}</span>
              <span className="review-why">{t.reasons[0]}</span>
              {t.flags.includes('possible_duplicate') && (
                <span className="review-why flag">⚠ possible duplicate charge</span>
              )}
            </div>
            <ConfidenceBadge band={t.band} confidence={t.confidence} />
            <span className={`review-amount ${t.amount > 0 ? 'pos' : 'neg'}`}>
              {money(t.amount)}
            </span>
            <CategorySelect row={t} onAssign={onAssign} />
          </li>
        ))}
      </ul>
    </section>
  )
}

export function CategorySelect({ row, onAssign }) {
  const SPENDING = [
    'Software & Subscriptions',
    'Travel',
    'Meals & Coffee',
    'Office & Equipment',
    'Marketing & Advertising',
    'Professional Services',
    'Personal & Non-Business',
  ]
  const options = [...SPENDING, 'Income', 'Transfers & Payments']
  const current = row.category ?? ''
  const needsRefundOption =
    row.category === 'Refunds' || row.linked_category === 'Refunds'

  return (
    <select
      className="category-select"
      value={current}
      aria-label={`Category for ${row.description}`}
      onChange={(e) => onAssign(row.id, e.target.value || null)}
    >
      <option value="">Needs Review…</option>
      {options.map((c) => (
        <option key={c} value={c}>
          {c}
        </option>
      ))}
      {needsRefundOption && <option value="Refunds">Refunds</option>}
    </select>
  )
}
