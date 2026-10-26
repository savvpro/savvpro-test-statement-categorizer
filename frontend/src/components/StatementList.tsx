import type { StatementListItem } from '../api/client'
import { formatDateTime, plural } from '../format'
import type { LoadStatus } from '../useStatement'

interface Props {
  statements: StatementListItem[]
  status: LoadStatus
  error: string
  selectedId: number | null
  onSelect: (id: number) => void
}

export function StatementList({ statements, status, error, selectedId, onSelect }: Props) {
  return (
    <section className="panel" aria-labelledby="statements-heading">
      <h2 id="statements-heading">Your statements</h2>
      {status === 'loading' && <p role="status">Loading statements…</p>}
      {status === 'error' && (
        <p role="alert" className="alert">
          {error}
        </p>
      )}
      {status === 'ready' && statements.length === 0 && (
        <p className="muted">No statements yet. Upload one to get started.</p>
      )}
      {statements.length > 0 && (
        <ul className="statement-list">
          {statements.map((statement) => (
            <li key={statement.id}>
              <button
                type="button"
                className="statement-item"
                aria-current={statement.id === selectedId ? 'true' : undefined}
                onClick={() => onSelect(statement.id)}
              >
                <span className="statement-name">{statement.filename}</span>
                <span className="statement-meta">
                  {formatDateTime(statement.uploaded_at)} · {plural(statement.row_count, 'row')} ·{' '}
                  {statement.needs_review_count > 0 ? (
                    <strong>{statement.needs_review_count} to review</strong>
                  ) : (
                    'all reviewed'
                  )}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
