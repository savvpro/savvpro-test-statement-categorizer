import { useEffect, useRef, useState } from 'react'
import { api, money } from './api'
import type { Statement, StatementDetail } from './api'
import { Icon } from './Icon'
import { TransactionTable } from './TransactionTable'
import { Upload } from './Upload'

export default function App() {
  const [statements, setStatements] = useState<Statement[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [detail, setDetail] = useState<StatementDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [savingId, setSavingId] = useState<number | null>(null)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const requestNumber = useRef(0)
  const summary = detail?.summary
  const busy = loading || uploading || savingId !== null || exporting

  useEffect(() => {
    let active = true
    async function initialize() {
      try {
        const [items, choices] = await Promise.all([
          api<Statement[]>('/statements'),
          api<string[]>('/categories'),
        ])
        const latest = items.length
          ? await api<StatementDetail>(`/statements/${items[0].id}`)
          : null
        if (active) {
          setStatements(items)
          setCategories(choices)
          setDetail(latest)
        }
      } catch (error) {
        if (active) setError((error as Error).message)
      } finally {
        if (active) setLoading(false)
      }
    }
    void initialize()
    return () => {
      active = false
    }
  }, [])

  async function openStatement(id: number) {
    const request = ++requestNumber.current
    setLoading(true)
    setError('')
    setNotice('')
    try {
      const next = await api<StatementDetail>(`/statements/${id}`)
      if (request === requestNumber.current) setDetail(next)
    } catch (error) {
      if (request === requestNumber.current) setError((error as Error).message)
    } finally {
      if (request === requestNumber.current) setLoading(false)
    }
  }

  async function upload(file: File) {
    setError('')
    setNotice('')
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError(
        'Choose a .csv file. PDF and spreadsheet files are not supported.',
      )
      return
    }
    if (file.size > 1024 * 1024) {
      setError('CSV files must be 1 MiB or smaller.')
      return
    }
    setUploading(true)
    try {
      const next = await api<StatementDetail>(
        `/statements?filename=${encodeURIComponent(file.name)}`,
        { method: 'POST', headers: { 'Content-Type': 'text/csv' }, body: file },
      )
      setStatements((items) => [next.statement, ...items])
      setDetail(next)
      setNotice(
        `Imported ${next.statement.transaction_count} transactions. ${next.summary.review_count} need review.`,
      )
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setUploading(false)
    }
  }

  async function loadSample() {
    setUploading(true)
    setError('')
    try {
      const response = await fetch('/developer-signed.csv')
      if (!response.ok)
        throw new Error(
          'The sample could not be loaded. Download a CSV sample from the format guide.',
        )
      const content = await response.text()
      await upload(
        new File([content], 'developer-signed.csv', { type: 'text/csv' }),
      )
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setUploading(false)
    }
  }

  async function correctCategory(id: number, category: string) {
    if (!detail) return
    setSavingId(id)
    setError('')
    setNotice('')
    try {
      const next = await api<StatementDetail>(
        `/statements/${detail.statement.id}/transactions/${id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category }),
        },
      )
      setDetail(next)
      setNotice('Category saved. Your totals are up to date.')
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setSavingId(null)
    }
  }

  async function exportStatement() {
    if (!detail) return
    setExporting(true)
    setError('')
    try {
      const response = await fetch(
        `/api/statements/${detail.statement.id}/export`,
      )
      if (!response.ok) throw new Error('The export failed. Please try again.')
      const url = URL.createObjectURL(await response.blob())
      const link = document.createElement('a')
      link.href = url
      link.download = `statement-${detail.statement.id}-categorized.csv`
      link.click()
      const revokeUrl = URL.revokeObjectURL.bind(URL)
      setTimeout(() => revokeUrl(url), 1000)
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setExporting(false)
    }
  }

  async function confirmDuplicate(id: number) {
    if (!detail) return
    setSavingId(id)
    setError('')
    setNotice('')
    try {
      const next = await api<StatementDetail>(
        `/statements/${detail.statement.id}/transactions/${id}/confirm-duplicate`,
        { method: 'POST' },
      )
      setDetail(next)
      setNotice(
        'Duplicate entry confirmed. Its category and amount are unchanged.',
      )
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setSavingId(null)
    }
  }

  const expenseGroups = summary
    ? Object.entries(summary.expense_categories)
        .filter(([, amount]) => Number(amount) > 0)
        .sort((a, b) => Number(b[1]) - Number(a[1]))
    : []
  const dates = detail?.transactions.map((row) => row.date).sort() ?? []

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href="/" aria-label="Ledgerly home">
            <span className="brand-icon">
              <Icon name="ledger" size={22} />
            </span>
            ledgerly<span className="brand-dot">.</span>
          </a>
          <span className="workspace-label">Freelancer workspace</span>
          <span className="local-label">
            <span /> Local workspace
          </span>
        </div>
      </header>
      <main>
        <div className="page-heading">
          <div>
            <p className="eyebrow">FREELANCE RECORDS · PAKISTAN</p>
            <h1>Statement overview</h1>
            <p>Review your PKR transactions, categories and totals.</p>
          </div>
          <button
            className="button export-button"
            disabled={!detail || busy}
            onClick={() => void exportStatement()}
          >
            <Icon name="download" size={17} />
            {exporting ? 'Preparing CSV...' : 'Export CSV'}
          </button>
        </div>
        <Upload
          busy={busy || !categories.length}
          onUpload={upload}
          onSample={loadSample}
        />
        {error && (
          <div className="error-message" role="alert">
            <Icon name="review" />
            <div>
              <strong>We couldn’t complete that.</strong>
              <p>{error}</p>
              {!categories.length && (
                <button
                  className="text-button"
                  onClick={() => window.location.reload()}
                >
                  Retry connection
                </button>
              )}
            </div>
          </div>
        )}
        <div className="live-notice" role="status" aria-live="polite">
          {uploading
            ? 'Reading and categorizing your statement...'
            : loading
              ? 'Loading your workspace...'
              : notice}
        </div>
        {detail && summary ? (
          <>
            <div className="statement-bar">
              <div>
                <span className="statement-icon">
                  <Icon name="file" size={18} />
                </span>
                <label htmlFor="statement-picker" className="visually-hidden">
                  Select statement
                </label>
                <select
                  id="statement-picker"
                  value={detail.statement.id}
                  disabled={busy}
                  onChange={(event) =>
                    void openStatement(Number(event.target.value))
                  }
                >
                  {statements.map((statement) => (
                    <option value={statement.id} key={statement.id}>
                      {statement.filename} (#{statement.id})
                    </option>
                  ))}
                </select>
                <span className="currency-label">{summary.currency}</span>
              </div>
              <span>
                {summary.transaction_count} transactions · {dates[0]} to{' '}
                {dates.at(-1)}
              </span>
            </div>
            <section className="summary-grid" aria-label="Statement summary">
              <article className="metric">
                <div>
                  <span>Total expenses</span>
                  <span className="metric-icon violet">
                    <Icon name="expense" size={18} />
                  </span>
                </div>
                <strong>{money(summary.expenses)}</strong>
                <p>Classified outgoing payments</p>
              </article>
              <article className="metric">
                <div>
                  <span>Identified income</span>
                  <span className="metric-icon green">
                    <Icon name="income" size={18} />
                  </span>
                </div>
                <strong>{money(summary.income)}</strong>
                <p>Explicit client payments</p>
              </article>
              <article className="metric">
                <div>
                  <span>Refunds</span>
                  <span className="metric-icon blue">
                    <Icon name="refund" size={18} />
                  </span>
                </div>
                <strong>{money(summary.refunds)}</strong>
                <p>Money back, shown separately</p>
              </article>
              <article className="metric">
                <div>
                  <span>Transfers</span>
                  <span className="metric-icon gray">
                    <Icon name="transfer" size={18} />
                  </span>
                </div>
                <strong>{money(summary.transfers)}</strong>
                <p>
                  {money(summary.transfers_in)} in ·{' '}
                  {money(summary.transfers_out)} out
                </p>
              </article>
            </section>
            <div className="insights-row">
              <section
                className={`review-panel ${summary.review_count ? '' : 'all-reviewed'}`}
              >
                <span className="review-icon">
                  <Icon
                    name={summary.review_count ? 'review' : 'check'}
                    size={23}
                  />
                </span>
                <div>
                  <h2>
                    {summary.review_count
                      ? `${summary.review_count} ${summary.review_count === 1 ? 'transaction needs' : 'transactions need'} review`
                      : 'No transactions need review'}
                  </h2>
                  <p>
                    {summary.review_count
                      ? 'Check uncertain categories and confirm any legitimate repeated entries.'
                      : 'You can still adjust any category before exporting.'}
                  </p>
                  <small>
                    Unclassified: {money(summary.unclassified_out)} out ·{' '}
                    {money(summary.unclassified_in)} in. Excluded from
                    classified totals.
                  </small>
                </div>
              </section>
              <section
                className="category-breakdown panel"
                aria-label="Expenses by category"
              >
                <h2>Where expenses went</h2>
                {expenseGroups.length ? (
                  expenseGroups.map(([category, amount], index) => (
                    <div className="breakdown-row" key={category}>
                      <span className={`category-dot dot-${index % 4}`} />
                      <span>{category}</span>
                      <strong>{money(amount)}</strong>
                    </div>
                  ))
                ) : (
                  <p>No classified expenses yet.</p>
                )}
              </section>
            </div>
            <TransactionTable
              key={detail.statement.id}
              transactions={detail.transactions}
              categories={categories}
              disabled={busy}
              savingId={savingId}
              onCorrect={correctCategory}
              onConfirmDuplicate={confirmDuplicate}
            />
            <div className="reconciliation">
              <span>
                Statement net movement{' '}
                <strong>{money(summary.net_movement)}</strong>
              </span>
              <span>
                Refunds are separate from income. Transfers are excluded from
                income and expenses.
              </span>
            </div>
          </>
        ) : (
          !loading && (
            <section className="empty-state panel">
              <span className="empty-icon">
                <Icon name="file" size={30} />
              </span>
              <h2>No statements imported yet.</h2>
              <p>
                Upload a PKR CSV to categorize transactions and review your
                freelance records, or try the fictional sample.
              </p>
              <button
                className="button"
                disabled={busy || !categories.length}
                onClick={() => void loadSample()}
              >
                Explore with fictional data
              </button>
            </section>
          )
        )}
        <footer>
          <span>
            ledgerly<span className="brand-dot">.</span>{' '}
            <span className="footer-divider">/</span> Freelance financial
            records
          </span>
          <span>
            For record keeping. Categories do not determine tax deductibility.
          </span>
        </footer>
      </main>
    </>
  )
}
