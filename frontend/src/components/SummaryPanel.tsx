import type { CurrencySummary, StatementSummary } from '../api/client'
import { formatAmount, plural } from '../format'
import type { LoadStatus } from '../useStatement'

interface Props {
  summary: StatementSummary | null
  status: LoadStatus
}

interface TileProps {
  label: string
  count: number // rows behind the figure; a tile with none is dimmed
  value?: string
  lines?: string[] // used instead of `value` when a tile shows several figures
  tag?: string // what the figure is not, e.g. "not spending"
}

function Tile({ label, count, value, lines, tag }: TileProps) {
  return (
    <div className={count === 0 ? 'tile tile--empty' : 'tile'}>
      <dt>{label}</dt>
      <dd>
        {lines ? lines.map((line) => <span key={line} className="tile-line">{line}</span>) : value}
      </dd>
      {tag && <p className="tile-note">{tag}</p>}
      <p className="tile-note">{plural(count, 'row')}</p>
    </div>
  )
}

function CurrencyBlock({ currency, data }: { currency: string; data: CurrencySummary }) {
  const money = (amount: string) => `${formatAmount(amount)} ${currency}`
  const headingId = `summary-${currency}`
  return (
    <section className="currency" aria-labelledby={headingId}>
      <h3 id={headingId}>{currency}</h3>
      <dl className="tiles">
        <Tile label="Total expenses" count={data.expenses.count} value={money(data.expenses.total)} />
        <Tile label="Fees" count={data.fees.count} value={money(data.fees.total)} />
        <Tile label="Income" count={data.income.count} value={money(data.income.total)} />
        <Tile label="Refunds" count={data.refunds.count} value={money(data.refunds.total)} />
        <Tile
          label="Tax already paid"
          count={data.tax_already_paid.count}
          value={money(data.tax_already_paid.total)}
        />
        <Tile
          label="Personal"
          count={data.personal.count}
          value={money(data.personal.total)}
          tag="not deductible"
        />
        <Tile
          label="Transfers"
          count={data.transfers.count}
          lines={[`In: ${money(data.transfers.total_in)}`, `Out: ${money(data.transfers.total_out)}`]}
          tag="not spending"
        />
        <Tile
          label="Unreviewed"
          count={data.needs_review.count}
          lines={[
            `In: ${money(data.needs_review.total_in)}`,
            `Out: ${money(data.needs_review.total_out)}`,
          ]}
          tag="not in any total"
        />
      </dl>
      {data.expenses_by_category.length > 0 ? (
        <table className="table table--compact">
          <caption>Expenses by category ({currency})</caption>
          <thead>
            <tr>
              <th scope="col">Category</th>
              <th scope="col" className="num">
                Rows
              </th>
              <th scope="col" className="num">
                Total
              </th>
            </tr>
          </thead>
          <tbody>
            {data.expenses_by_category.map((row) => (
              <tr key={row.category}>
                <th scope="row">{row.category}</th>
                <td className="num">{row.count}</td>
                <td className="num">{formatAmount(row.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="muted">No expenses categorized yet in {currency}.</p>
      )}
    </section>
  )
}

export function SummaryPanel({ summary, status }: Props) {
  const currencies = summary ? Object.entries(summary.currencies) : []
  return (
    <section className="panel" aria-labelledby="summary-heading">
      <h2 id="summary-heading">Summary</h2>
      <p className="muted">
        Each currency is totalled on its own and never converted. These figures help you prepare
        for tax time; they are not tax advice.
      </p>
      {status === 'loading' && <p role="status">Loading summary…</p>}
      {status === 'error' && <p className="muted">The summary could not be loaded.</p>}
      {status === 'ready' && currencies.length === 0 && (
        <p className="muted">Nothing to total yet. Fix the rows that need review.</p>
      )}
      {currencies.map(([currency, data]) => (
        <CurrencyBlock key={currency} currency={currency} data={data} />
      ))}
    </section>
  )
}
