import { useState } from 'react'
import type { Transaction } from './api'
import { money } from './api'
import { Icon } from './Icon'

interface TableProps {
  transactions: Transaction[]
  categories: string[]
  disabled: boolean
  savingId: number | null
  onCorrect: (id: number, category: string) => Promise<void>
  onConfirmDuplicate: (id: number) => Promise<void>
}

const PAGE_SIZE = 25

export function TransactionTable({
  transactions,
  categories,
  disabled,
  savingId,
  onCorrect,
  onConfirmDuplicate,
}: TableProps) {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [reviewOnly, setReviewOnly] = useState(false)
  const [page, setPage] = useState(1)
  const filtered = transactions.filter(
    (transaction) =>
      transaction.description.toLowerCase().includes(search.toLowerCase()) &&
      (!category || transaction.category === category) &&
      (!reviewOnly || transaction.needs_review),
  )
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, pages)
  const shown = filtered.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE,
  )

  return (
    <section
      className="transactions panel"
      aria-labelledby="transactions-title"
    >
      <div className="section-heading">
        <div>
          <h2 id="transactions-title">
            Transactions <span className="count">{transactions.length}</span>
          </h2>
          <p>
            Check explanations, edit categories and confirm repeated entries.
          </p>
        </div>
        <span className="autosave">
          <Icon name="check" size={15} /> Corrections save automatically
        </span>
      </div>
      <div className="table-tools">
        <label className="search-field">
          <Icon name="search" size={17} />
          <input
            aria-label="Search transactions"
            placeholder="Search descriptions..."
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
          />
        </label>
        <select
          aria-label="Filter by category"
          value={category}
          onChange={(event) => {
            setCategory(event.target.value)
            setPage(1)
          }}
        >
          <option value="">All categories</option>
          {categories.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <label className="review-toggle">
          <input
            type="checkbox"
            checked={reviewOnly}
            onChange={(event) => {
              setReviewOnly(event.target.checked)
              setPage(1)
            }}
          />{' '}
          Needs review only
        </label>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Description / explanation</th>
              <th scope="col" className="amount">
                Amount
              </th>
              <th scope="col">Category</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((transaction) => (
              <tr key={transaction.id}>
                <td className="date-cell">
                  <time dateTime={transaction.date}>
                    {new Intl.DateTimeFormat('en-GB', {
                      day: '2-digit',
                      month: 'short',
                      timeZone: 'UTC',
                    }).format(new Date(transaction.date))}
                  </time>
                  <small>{transaction.date.slice(0, 4)}</small>
                </td>
                <td className="description-cell">
                  <strong>{transaction.description}</strong>
                  <p>{transaction.explanation}</p>
                  {transaction.possible_duplicate && (
                    <span className="duplicate-label">
                      {transaction.duplicate_confirmed
                        ? 'Repeated entry confirmed · retained'
                        : 'Possible duplicate · retained'}
                    </span>
                  )}
                  {transaction.manually_corrected && (
                    <details className="original-rule">
                      <summary>Original decision</summary>
                      {transaction.automatic_category}:{' '}
                      {transaction.automatic_explanation}
                    </details>
                  )}
                </td>
                <td
                  className={`amount ${Number(transaction.amount) > 0 ? 'positive' : ''}`}
                >
                  {Number(transaction.amount) > 0 ? '+' : ''}
                  {money(transaction.amount)}
                </td>
                <td className="category-cell">
                  <select
                    className="category-select"
                    aria-label={`Category for ${transaction.description}, row ${transaction.row_number}`}
                    value={transaction.category}
                    disabled={disabled}
                    onChange={(event) =>
                      void onCorrect(transaction.id, event.target.value)
                    }
                  >
                    {categories.map((item) => (
                      <option key={item}>{item}</option>
                    ))}
                  </select>
                </td>
                <td className="status-cell">
                  <span
                    className={`status ${transaction.needs_review ? 'needs-review' : transaction.manually_corrected ? 'corrected' : 'categorized'}`}
                  >
                    {savingId === transaction.id
                      ? 'Saving...'
                      : transaction.needs_review
                        ? 'Needs review'
                        : transaction.manually_corrected
                          ? 'Corrected'
                          : 'Categorized'}
                  </span>
                  {transaction.manually_corrected &&
                    transaction.needs_review && (
                      <span className="correction-label">
                        Category corrected
                      </span>
                    )}
                  {transaction.possible_duplicate &&
                    !transaction.duplicate_confirmed && (
                      <button
                        className="confirm-button"
                        disabled={disabled}
                        onClick={() => void onConfirmDuplicate(transaction.id)}
                      >
                        Confirm entry
                      </button>
                    )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!shown.length && (
          <div className="no-results">
            No matching transactions. Try another search or filter.
          </div>
        )}
      </div>
      <div className="table-footer">
        <span>
          {filtered.length ? (currentPage - 1) * PAGE_SIZE + 1 : 0} to{' '}
          {Math.min(currentPage * PAGE_SIZE, filtered.length)} of{' '}
          {filtered.length} transactions
        </span>
        <div>
          <button
            className="button small"
            disabled={currentPage <= 1}
            onClick={() => setPage(currentPage - 1)}
          >
            Previous
          </button>
          <span>
            Page {currentPage} of {pages}
          </span>
          <button
            className="button small"
            disabled={currentPage >= pages}
            onClick={() => setPage(currentPage + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  )
}
