import { useState } from 'react'
import { colorFor } from '../categories'
import { money } from '../format'
import { Panel } from './ui'

function Figure({ label, value, currency, tone }) {
  return (
    <div>
      <div className="text-sm text-ink-soft">{label}</div>
      <div className={`tabular font-display text-2xl font-bold tracking-tight sm:text-3xl ${tone}`}>
        {Number(value) < 0 ? '−' : ''}
        {money(value, currency)}
      </div>
    </div>
  )
}

function Spending({ totals }) {
  const parts = totals.categories
    .filter((c) => c.kind === 'expense' && Number(c.total) < 0)
    .map((c) => ({ ...c, spent: -Number(c.total) }))
  const whole = parts.reduce((sum, p) => sum + p.spent, 0)
  if (!whole) return <p className="text-sm text-ink-soft">No business spending has been decided yet.</p>

  return (
    <div>
      <div className="flex h-4 w-full gap-0.5 overflow-hidden rounded-full bg-paper" aria-hidden="true">
        {parts.map((p) => (
          <div
            key={p.category}
            title={`${p.category}: ${money(p.spent, totals.currency)}`}
            className="h-full transition-[width] duration-700 ease-out"
            style={{ width: `${(p.spent / whole) * 100}%`, backgroundColor: colorFor(p.category) }}
          />
        ))}
      </div>
      <ul className="mt-3 grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
        {parts.map((p) => (
          <li key={p.category} className="flex items-center gap-2 text-sm">
            <span className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: colorFor(p.category) }} />
            <span className="min-w-0 flex-1 truncate">{p.category}</span>
            <span className="tabular font-medium">{money(p.spent, totals.currency)}</span>
            <span className="tabular w-10 text-right text-ink-soft">{Math.round((p.spent / whole) * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function TotalsPanel({ summary, onShowReview }) {
  const currencies = summary?.currencies ?? []
  const [picked, setPicked] = useState(null)
  const totals = currencies.find((c) => c.currency === picked) ?? currencies[0]

  if (!totals) {
    return (
      <Panel title="Totals">
        <p className="text-ink-soft">
          Upload a statement and the totals for each currency show up here. PKR and USD are always kept apart.
        </p>
      </Panel>
    )
  }

  const switcher = currencies.length > 1 && (
    <div className="inline-flex gap-1 rounded-xl bg-paper p-1" role="tablist" aria-label="Currency">
      {currencies.map((c) => (
        <button
          key={c.currency}
          role="tab"
          aria-selected={c.currency === totals.currency}
          onClick={() => setPicked(c.currency)}
          className={`rounded-lg px-3 py-1 text-sm ${
            c.currency === totals.currency ? 'bg-ink font-medium text-white' : 'text-ink-soft hover:text-ink'
          }`}
        >
          {c.currency}
        </button>
      ))}
    </div>
  )

  const inOut = (out, into) =>
    [Number(out) && `${money(out, totals.currency)} out`, Number(into) && `${money(into, totals.currency)} in`]
      .filter(Boolean)
      .join(', ')
  const notCounted = [
    inOut(totals.transfers_out, totals.transfers_in) && `Transfers between your accounts: ${inOut(totals.transfers_out, totals.transfers_in)}`,
    inOut(totals.personal_out, totals.personal_in) && `Personal: ${inOut(totals.personal_out, totals.personal_in)}`,
  ].filter(Boolean)

  return (
    <Panel title={`Totals in ${totals.currency}`} aside={switcher}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Figure label="Business income" value={totals.income} currency={totals.currency} tone="text-emerald" />
        <Figure label="Business spending" value={totals.spending} currency={totals.currency} tone="text-ink" />
        <Figure
          label="Income minus spending"
          value={totals.net}
          currency={totals.currency}
          tone={Number(totals.net) < 0 ? 'text-brick' : 'text-ink'}
        />
      </div>
      {Number(totals.tax_deducted) > 0 && (
        <p className="mt-3 text-sm text-ink-soft">
          Tax already taken by the bank: <span className="tabular font-medium text-ink">{money(totals.tax_deducted, totals.currency)}</span>
        </p>
      )}

      <h3 className="mt-6 mb-3 font-display text-base font-bold">Where the business money went</h3>
      <Spending totals={totals} />

      <div className="mt-6 space-y-2 border-t border-line pt-4 text-sm">
        {totals.review_count > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-marigold-soft px-3 py-2">
            <span>
              <strong>{totals.review_count}</strong> {totals.review_count === 1 ? 'row is' : 'rows are'} waiting for you
              and not counted yet ({inOut(totals.review_out, totals.review_in)}).
            </span>
            <button onClick={onShowReview} className="font-medium text-ink underline underline-offset-2">
              Review them
            </button>
          </div>
        )}
        {notCounted.map((line) => (
          <p key={line} className="text-ink-soft">
            Not counted: {line}
          </p>
        ))}
        {summary.unreadable_rows > 0 && (
          <p className="text-[#9c1450]">
            {summary.unreadable_rows} {summary.unreadable_rows === 1 ? 'row' : 'rows'} couldn't be read, so these
            totals may be incomplete. See the import report.
          </p>
        )}
      </div>
    </Panel>
  )
}
