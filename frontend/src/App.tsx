import { useCallback, useEffect, useState } from 'react'
import { ApiError, api } from './api/client'
import type { UploadOptions } from './api/client'
import type { AccountType, Category, Statement, StatementDetail, Summary, Transaction } from './api/types'
import { ErrorBanner } from './components/ErrorBanner'
import { Header } from './components/Header'
import { ImportNotes } from './components/ImportNotes'
import { StatementList } from './components/StatementList'
import { SummaryCards } from './components/SummaryCards'
import { Toast } from './components/Toast'
import { TransactionTable } from './components/TransactionTable'
import { UploadPanel } from './components/UploadPanel'

const message = (error: unknown) => (error instanceof Error ? error.message : 'Something went wrong')

export default function App() {
  const [categories, setCategories] = useState<Category[]>([])
  const [statements, setStatements] = useState<Statement[]>([])
  const [reviewCounts, setReviewCounts] = useState<Record<number, number>>({})
  const [detail, setDetail] = useState<StatementDetail | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [busy, setBusy] = useState(false)
  const [duplicateOf, setDuplicateOf] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const closeToast = useCallback(() => setToast(null), [])

  const refreshList = useCallback(async () => setStatements(await api.listStatements()), [])

  useEffect(() => {
    Promise.all([api.categories(), api.listStatements()])
      .then(([cats, list]) => {
        setCategories(cats)
        setStatements(list)
      })
      .catch((e: unknown) => setError(message(e)))
  }, [])

  const show = (next: StatementDetail, rows: Transaction[], totals: Summary) => {
    setDetail(next)
    setTransactions(rows)
    setSummary(totals)
    setReviewCounts((counts) => ({ ...counts, [next.id]: next.review_count }))
  }

  const openStatement = async (id: number) => {
    setError(null)
    setDuplicateOf(null)
    try {
      const [next, rows, totals] = await Promise.all([
        api.getStatement(id),
        api.listTransactions(id),
        api.getSummary(id),
      ])
      show(next, rows, totals)
    } catch (e) {
      setError(message(e))
    }
  }

  const upload = async (file: File, options: UploadOptions) => {
    setBusy(true)
    setError(null)
    setDuplicateOf(null)
    try {
      const created = await api.uploadStatement(file, options)
      show(created, created.transactions, await api.getSummary(created.id))
      await refreshList()
    } catch (e) {
      if (e instanceof ApiError && e.status === 409 && e.statementId != null) setDuplicateOf(e.statementId)
      else setError(message(e))
    } finally {
      setBusy(false)
    }
  }

  const uploadSample = async (name: string, accountType: AccountType) => {
    try {
      await upload(await api.fetchSample(name), { accountType })
    } catch (e) {
      setError(message(e))
    }
  }

  const remove = async (id: number) => {
    if (!window.confirm('Delete this statement and its transactions?')) return
    try {
      await api.deleteStatement(id)
      if (detail?.id === id) {
        setDetail(null)
        setSummary(null)
        setTransactions([])
      }
      await refreshList()
    } catch (e) {
      setError(message(e))
    }
  }

  const save = async (txn: Transaction, categoryId: string, remember: boolean) => {
    setError(null)
    try {
      const result = await api.updateTransaction(txn.id, categoryId, remember)
      const [rows, totals] = await Promise.all([
        api.listTransactions(txn.statement_id),
        api.getSummary(txn.statement_id),
      ])
      setTransactions(rows)
      setSummary(totals)
      setReviewCounts((counts) => ({
        ...counts,
        [txn.statement_id]: rows.filter((r) => r.status === 'needs_review').length,
      }))
      const others = result.updated_count
      setToast(
        others > 0
          ? `Updated ${others} other transaction${others === 1 ? '' : 's'}`
          : remember
            ? 'Saved. Future uploads from this merchant will use it.'
            : 'Saved',
      )
    } catch (e) {
      setError(message(e))
    }
  }

  return (
    <div className="app">
      <Header />
      <main>
        {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
        <div className="layout">
          <aside className="sidebar">
            <UploadPanel
              busy={busy}
              duplicateOf={duplicateOf}
              onUpload={upload}
              onSample={uploadSample}
              onOpenExisting={openStatement}
            />
            <StatementList
              statements={statements}
              selectedId={detail?.id ?? null}
              reviewCounts={reviewCounts}
              onSelect={openStatement}
              onDelete={remove}
            />
          </aside>
          <div className="content">
            {detail && summary ? (
              <>
                <div className="statement-title">
                  <h2>{detail.filename}</h2>
                  <span className="muted">
                    {detail.account_type === 'credit_card' ? 'Credit card' : 'Checking'} ·{' '}
                    {detail.row_count} rows
                  </span>
                </div>
                <SummaryCards summary={summary} />
                <ImportNotes statement={detail} />
                <TransactionTable
                  key={detail.id}
                  transactions={transactions}
                  categories={categories}
                  exportUrl={api.exportUrl(detail.id)}
                  onSave={save}
                />
              </>
            ) : (
              <div className="card empty-state">
                <h2>No statement open</h2>
                <p className="muted">
                  Upload a CSV or Excel export from your bank or card, or try one of the samples. Rows
                  the rules are sure about are categorized automatically; the rest wait for you in
                  Needs Review, each with the reason why.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
      <footer className="footer muted small">
        Estimates only, not tax advice. Categories follow common Schedule C defaults; check with a
        tax professional before filing.
      </footer>
      {toast && <Toast message={toast} onClose={closeToast} />}
    </div>
  )
}
