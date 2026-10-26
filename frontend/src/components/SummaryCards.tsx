import type { CategoryTotal, Summary } from '../api/types'
import { formatMoney } from '../format'

function TotalsTable({ rows, caption, showDeductible }: { rows: CategoryTotal[]; caption: string; showDeductible: boolean }) {
  return (
    <div className="table-scroll">
      <table className="totals">
        <caption>{caption}</caption>
        <thead>
          <tr>
            <th scope="col">Category</th>
            <th scope="col">Schedule C line</th>
            <th scope="col" className="num">Total</th>
            {showDeductible && <th scope="col" className="num">Deductible</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.category_id}>
              <td>
                {row.label} <span className="muted small">({row.count})</span>
              </td>
              <td className="muted">{row.schedule_c_line ?? '-'}</td>
              <td className="num">{formatMoney(row.total)}</td>
              {showDeductible && (
                <td className="num">{row.kind === 'expense' ? formatMoney(row.deductible) : '-'}</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function SummaryCards({ summary }: { summary: Summary }) {
  const cards = [
    { label: 'Income', value: formatMoney(summary.income), tone: 'in' },
    { label: 'Business expenses', value: formatMoney(summary.expenses), tone: 'out' },
    { label: 'Est. deductible', value: formatMoney(summary.estimated_deductible), tone: '' },
    {
      label: 'Needs review',
      value: String(summary.needs_review_count),
      sub: `${formatMoney(summary.needs_review_amount)} not yet counted`,
      tone: summary.needs_review_count > 0 ? 'warn' : '',
    },
  ]
  return (
    <section aria-labelledby="summary-title">
      <h2 id="summary-title" className="visually-hidden">
        Summary
      </h2>
      <div className="cards">
        {cards.map((card) => (
          <div key={card.label} className={`card stat ${card.tone}`}>
            <span className="stat-label">{card.label}</span>
            <span className="stat-value" data-testid={`stat-${card.label}`}>
              {card.value}
            </span>
            {card.sub && <span className="muted small">{card.sub}</span>}
          </div>
        ))}
      </div>

      <div className="card">
        {summary.categories.length > 0 ? (
          <TotalsTable rows={summary.categories} caption="Business income and expenses" showDeductible />
        ) : (
          <p className="muted">No categorized business rows yet.</p>
        )}
        {summary.non_operating.length > 0 && (
          <TotalsTable
            rows={summary.non_operating}
            caption="Not business income or expense (transfers, card payments, personal)"
            showDeductible={false}
          />
        )}
        <p className="muted small">
          Refunds linked to a purchase are netted into that category.
          {summary.unlinked_refund_count > 0 &&
            ` ${summary.unlinked_refund_count} unmatched refund(s) totalling ${formatMoney(summary.unlinked_refunds)} are not counted as income.`}
          {summary.pending_count > 0 && ` ${summary.pending_count} pending row(s) are excluded.`}
        </p>
      </div>
    </section>
  )
}
