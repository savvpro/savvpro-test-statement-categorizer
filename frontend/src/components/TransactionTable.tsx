import { useMemo, useState } from 'react'
import type { Category, Transaction, TxnStatus } from '../api/types'
import { TransactionRow } from './TransactionRow'

type Tab = 'all' | TxnStatus
const TABS: { id: Tab; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'needs_review', label: 'Needs Review' },
  { id: 'auto', label: 'Auto' },
  { id: 'user_confirmed', label: 'Confirmed' },
]

interface Props {
  transactions: Transaction[]
  categories: Category[]
  exportUrl: string
  onSave: (txn: Transaction, categoryId: string, remember: boolean) => Promise<void>
}

export function TransactionTable({ transactions, categories, exportUrl, onSave }: Props) {
  const [tab, setTab] = useState<Tab>(() =>
    transactions.some((t) => t.status === 'needs_review') ? 'needs_review' : 'all',
  )
  const [query, setQuery] = useState('')

  const counts = useMemo(() => {
    const result: Record<Tab, number> = { all: transactions.length, auto: 0, needs_review: 0, user_confirmed: 0 }
    for (const t of transactions) result[t.status] += 1
    return result
  }, [transactions])

  const labels = useMemo(() => Object.fromEntries(categories.map((c) => [c.id, c.label])), [categories])
  const needle = query.trim().toLowerCase()
  const visible = transactions.filter(
    (t) =>
      (tab === 'all' || t.status === tab) &&
      (!needle ||
        t.description_raw.toLowerCase().includes(needle) ||
        t.merchant_key.toLowerCase().includes(needle) ||
        (labels[t.category_id] ?? '').toLowerCase().includes(needle)),
  )

  return (
    <section className="card" aria-labelledby="txn-title">
      <div className="table-header">
        <h2 id="txn-title">Transactions</h2>
        <div className="table-tools">
          <input
            type="search"
            placeholder="Search description or category"
            aria-label="Search transactions"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <a className="button button-ghost" href={exportUrl} download>
            Export CSV
          </a>
        </div>
      </div>

      <div className="tabs" role="tablist" aria-label="Filter by status">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            className={tab === id ? 'tab active' : 'tab'}
            onClick={() => setTab(id)}
          >
            {label} <span className="count">{counts[id]}</span>
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <p className="empty-rows muted">
          {tab === 'needs_review' && !needle ? 'All caught up: nothing left to review.' : 'No matching transactions.'}
        </p>
      ) : (
        <div className="table-scroll">
          <table className="transactions" aria-labelledby="txn-title">
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Description</th>
                <th scope="col" className="num">Amount</th>
                <th scope="col">Category</th>
                <th scope="col">Confidence</th>
                <th scope="col">Status</th>
                <th scope="col">
                  <span className="visually-hidden">Reasons</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {visible.map((txn) => (
                <TransactionRow
                  key={`${txn.id}-${txn.updated_at}`}
                  txn={txn}
                  categories={categories}
                  labels={labels}
                  onSave={onSave}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
