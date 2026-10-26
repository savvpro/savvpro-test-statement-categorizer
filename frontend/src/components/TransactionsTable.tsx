import { Fragment, useState } from 'react'
import type { CorrectionBody, Transaction } from '../api/client'
import {
  amountDirection,
  formatAmount,
  formatConfidence,
  formatDate,
} from '../format'
import { ReviewEditor } from './ReviewEditor'

type Filter = 'all' | 'review' | 'fixed'

interface Props {
  transactions: Transaction[]
  categories: string[]
  kinds: string[]
  editingId: number | null
  saving: boolean
  saveError: string
  onEdit: (id: number | null) => void
  onSave: (transaction: Transaction, body: CorrectionBody) => void
}

const FILTERS: { id: Filter; label: string; matches: (t: Transaction) => boolean }[] = [
  { id: 'all', label: 'All', matches: () => true },
  { id: 'review', label: 'Needs Review', matches: (t) => t.needs_review },
  { id: 'fixed', label: 'Fixed by me', matches: (t) => t.edited_by_user },
]

const COLUMNS = 9

// A row in review has no category yet, so a confidence figure would be misleading: the
// number the API holds belongs to the rule that sent the row to review.
const NO_CONFIDENCE_HINT =
  'No confidence is shown for rows that need review. The number belongs to the rule that ' +
  'flagged the row, not to a category guess.'

export function TransactionsTable({
  transactions,
  categories,
  kinds,
  editingId,
  saving,
  saveError,
  onEdit,
  onSave,
}: Props) {
  const [filter, setFilter] = useState<Filter>('all')
  const active = FILTERS.find((f) => f.id === filter) ?? FILTERS[0]
  const visible = transactions.filter(active.matches)

  return (
    <section className="panel" aria-labelledby="transactions-heading">
      <h2 id="transactions-heading">Transactions</h2>
      <div className="filters" role="group" aria-label="Show rows">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            className="filter"
            aria-pressed={f.id === filter}
            onClick={() => setFilter(f.id)}
          >
            {f.label} <span className="filter-count">{transactions.filter(f.matches).length}</span>
          </button>
        ))}
      </div>
      {transactions.length === 0 ? (
        <p className="muted">No transactions could be read from this file.</p>
      ) : visible.length === 0 ? (
        <p className="muted">No rows in this view.</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <caption className="visually-hidden">Transactions: {active.label}</caption>
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">Date</th>
                <th scope="col">Description</th>
                <th scope="col" className="num">
                  Amount
                </th>
                <th scope="col">Category</th>
                <th scope="col">Kind</th>
                <th scope="col" className="num">
                  Confidence
                </th>
                <th scope="col">Reason</th>
                <th scope="col">
                  <span className="visually-hidden">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {visible.map((t) => (
                <Fragment key={t.id}>
                  <tr className={t.needs_review ? 'row--review' : undefined}>
                    <td>{t.row_number}</td>
                    <td className="nowrap">{formatDate(t.date)}</td>
                    <td className="description">{t.raw_description}</td>
                    <td className={`num nowrap amount amount--${amountDirection(t.amount)}`}>
                      {formatAmount(t.amount)} <span className="currency-code">{t.currency}</span>
                    </td>
                    <td>
                      {t.category}
                      {t.needs_review && <span className="badge badge--review">Needs review</span>}
                      {t.edited_by_user && <span className="badge">Fixed by me</span>}
                      {t.suggested_category && (
                        <span className="suggestion">Suggested: {t.suggested_category}</span>
                      )}
                    </td>
                    <td>{t.kind}</td>
                    <td className="num">
                      {t.needs_review ? (
                        <span title={NO_CONFIDENCE_HINT}>
                          —<span className="visually-hidden"> not shown, this row needs review</span>
                        </span>
                      ) : (
                        formatConfidence(t.confidence)
                      )}
                    </td>
                    <td className="reason">{t.reason}</td>
                    <td>
                      <button
                        type="button"
                        className={t.needs_review ? 'primary' : undefined}
                        aria-label={`${t.needs_review ? 'Fix' : 'Edit'} row ${t.row_number}`}
                        aria-expanded={editingId === t.id}
                        onClick={() => onEdit(editingId === t.id ? null : t.id)}
                      >
                        {t.needs_review ? 'Fix' : 'Edit'}
                      </button>
                    </td>
                  </tr>
                  {editingId === t.id && (
                    <tr className="editor-row">
                      <td colSpan={COLUMNS}>
                        <ReviewEditor
                          transaction={t}
                          categories={categories}
                          kinds={kinds}
                          saving={saving}
                          error={saveError}
                          onSave={(body) => onSave(t, body)}
                          onCancel={() => onEdit(null)}
                        />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
