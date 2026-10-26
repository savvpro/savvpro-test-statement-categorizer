import type { Statement } from '../api/types'
import { formatDate } from '../format'

interface Props {
  statements: Statement[]
  selectedId: number | null
  reviewCounts: Record<number, number>
  onSelect: (id: number) => void
  onDelete: (id: number) => void
}

export function StatementList({ statements, selectedId, reviewCounts, onSelect, onDelete }: Props) {
  if (statements.length === 0) return null
  return (
    <section className="card" aria-labelledby="statements-title">
      <h2 id="statements-title">Your statements</h2>
      <ul className="statement-list">
        {statements.map((s) => (
          <li key={s.id} className={s.id === selectedId ? 'selected' : undefined}>
            <button type="button" className="statement-select" onClick={() => onSelect(s.id)}>
              <span className="statement-name">{s.filename}</span>
              <span className="muted small">
                {formatDate(s.uploaded_at)} · {s.row_count} rows
                {reviewCounts[s.id] != null && ` · ${reviewCounts[s.id]} to review`}
              </span>
            </button>
            <button
              type="button"
              className="link-button danger"
              onClick={() => onDelete(s.id)}
              aria-label={`Delete ${s.filename}`}
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
