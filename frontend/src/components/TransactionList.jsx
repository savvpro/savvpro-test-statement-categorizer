import { useMemo, useState } from 'react'
import { colorFor } from '../categories'
import { shortDate, signedMoney } from '../format'
import { Button, CategoryChip, CategorySelect } from './ui'

const FILTERS = [
  { value: 'needs_review', label: 'Needs review' },
  { value: 'all', label: 'All' },
  { value: 'auto', label: 'Sorted by rules' },
  { value: 'user_corrected', label: 'Changed by you' },
]

function Editor({ row, categories, initial, onSave, onCancel, saveLabel }) {
  const [choice, setChoice] = useState(initial ?? '')
  const [busy, setBusy] = useState(false)
  async function save() {
    setBusy(true)
    try {
      await onSave(choice)
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="min-w-44 flex-1">
        <CategorySelect
          id={`category-${row.id}`}
          categories={categories}
          value={choice}
          onChange={setChoice}
          money={Number(row.amount) < 0 ? 'out' : 'in'}
        />
      </div>
      <Button onClick={save} disabled={!choice || busy} className="py-1.5">
        {saveLabel}
      </Button>
      {onCancel && (
        <button onClick={onCancel} className="text-sm text-ink-soft underline underline-offset-2">
          Cancel
        </button>
      )}
    </div>
  )
}

function Row({ row, categories, offer, onCorrect, onUndo, onMakeRule, onDismissOffer }) {
  const [editing, setEditing] = useState(false)
  const review = row.status === 'needs_review'
  const edge = review ? '#f4a300' : colorFor(row.category)

  return (
    <li className="border-b border-line last:border-b-0">
      <div className="grid gap-x-5 gap-y-2 py-4 pr-1 pl-4 md:grid-cols-[6.5rem_minmax(0,1fr)_8.5rem_minmax(15rem,0.9fr)]" style={{ boxShadow: `inset 4px 0 0 ${edge}` }}>
        <div className="tabular text-sm text-ink-soft md:pt-0.5">{shortDate(row.date)}</div>

        <div className="min-w-0">
          <div className="font-medium break-words">{row.description}</div>
          <p className={`mt-1 text-sm ${review ? 'text-[#7a5200]' : 'text-ink-soft'}`}>{row.reason}</p>
          <div className="mt-1 text-xs text-ink-soft">
            {row.source_row} in {row.source_file}
            {row.rule_id && <>, rule {row.rule_id}</>}
          </div>
        </div>

        <div className={`tabular text-left font-medium md:pt-0.5 md:text-right ${Number(row.amount) > 0 ? 'text-emerald' : ''}`}>
          {signedMoney(row.amount, row.currency)}
        </div>

        <div className="md:pt-0.5">
          {review ? (
            <Editor
              row={row}
              categories={categories}
              initial={row.suggested_category}
              saveLabel={row.suggested_category ? 'Confirm' : 'Save'}
              onSave={(category) => onCorrect(row, category)}
            />
          ) : editing ? (
            <Editor
              row={row}
              categories={categories}
              initial={row.category}
              saveLabel="Save"
              onCancel={() => setEditing(false)}
              onSave={async (category) => {
                await onCorrect(row, category)
                setEditing(false)
              }}
            />
          ) : (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <CategoryChip name={row.category} />
              {row.type === 'refund' && <span className="text-xs text-ink-soft">refund</span>}
              <button onClick={() => setEditing(true)} className="text-sm text-ink-soft underline underline-offset-2 hover:text-ink">
                Change
              </button>
              {row.status === 'user_corrected' && (
                <button onClick={() => onUndo(row)} className="text-sm text-ink-soft underline underline-offset-2 hover:text-ink">
                  Undo my change
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {offer && (
        <div className="mb-4 ml-4 flex flex-wrap items-center gap-3 rounded-xl bg-lapis-soft px-4 py-3 text-sm">
          <span className="flex-1">
            Put every description containing <strong>{offer.pattern}</strong> in <strong>{offer.category}</strong> from now on?
          </span>
          <Button onClick={() => onMakeRule(offer, row)} className="py-1.5">
            Make a rule
          </Button>
          <button onClick={onDismissOffer} className="text-ink-soft underline underline-offset-2">
            Not now
          </button>
        </div>
      )}
    </li>
  )
}

export default function TransactionList({ rows, categories, filter, onFilter, offer, keepVisible, ...handlers }) {
  const [search, setSearch] = useState('')
  const counts = useMemo(() => {
    const result = { all: rows.length, needs_review: 0, auto: 0, user_corrected: 0 }
    rows.forEach((r) => (result[r.status] += 1))
    return result
  }, [rows])

  const visible = rows.filter(
    (r) =>
      (filter === 'all' || r.status === filter || keepVisible.has(r.id)) &&
      (!search || r.description.toLowerCase().includes(search.toLowerCase())),
  )

  return (
    <section className="rounded-2xl border border-line bg-white">
      <div className="flex flex-wrap items-center gap-3 border-b border-line px-5 py-4">
        <h2 className="mr-2 font-display text-xl font-bold tracking-tight">Transactions</h2>
        <div className="flex flex-wrap gap-1" role="tablist" aria-label="Show">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              role="tab"
              aria-selected={filter === f.value}
              onClick={() => onFilter(f.value)}
              className={`rounded-lg px-3 py-1.5 text-sm ${
                filter === f.value ? 'bg-paper font-medium text-ink' : 'text-ink-soft hover:text-ink'
              }`}
            >
              {f.label}
              <span
                className={`tabular ml-1.5 rounded-full px-1.5 text-xs ${
                  f.value === 'needs_review' && counts.needs_review ? 'bg-marigold font-semibold text-ink' : 'bg-paper'
                }`}
              >
                {counts[f.value]}
              </span>
            </button>
          ))}
        </div>
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search descriptions"
          aria-label="Search descriptions"
          className="ml-auto w-full rounded-lg border border-line px-3 py-1.5 text-sm sm:w-56"
        />
      </div>

      {visible.length === 0 ? (
        <p className="px-5 py-10 text-center text-ink-soft">
          {rows.length === 0
            ? 'No transactions yet. Upload a statement to see every row and the reason behind its category.'
            : filter === 'needs_review' && !search
              ? 'Nothing needs review. Every row here has a category.'
              : 'No rows match.'}
        </p>
      ) : (
        <ul>
          {visible.map((row) => (
            <Row
              key={row.id}
              row={row}
              categories={categories}
              offer={offer?.txnId === row.id ? offer : null}
              {...handlers}
            />
          ))}
        </ul>
      )}
    </section>
  )
}
