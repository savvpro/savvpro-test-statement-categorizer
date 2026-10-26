import type { StatementDetail } from '../api/client'

export function CountsBar({ statement }: { statement: StatementDetail }) {
  const rows = statement.transactions
  const autoCategorized = rows.filter((t) => !t.needs_review && !t.edited_by_user).length
  const items = [
    { label: 'Rows', value: rows.length },
    { label: 'Auto-categorized', value: autoCategorized },
    { label: 'Needs review', value: statement.needs_review_count, warn: true },
    { label: 'Parse errors', value: statement.parse_errors.length, warn: true },
  ]
  return (
    <dl className="counts" aria-label="Statement counts">
      {items.map((item) => (
        <div key={item.label} className={item.warn && item.value > 0 ? 'count count--warn' : 'count'}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}
