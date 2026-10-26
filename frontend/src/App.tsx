import { useCallback, useEffect, useState } from 'react'
import {
  correctTransaction,
  errorMessage,
  exportUrl,
  getCategories,
  listStatements,
  type Categories,
  type CorrectionBody,
  type StatementDetail,
  type StatementListItem,
  type Transaction,
} from './api/client'
import { CountsBar } from './components/CountsBar'
import { ParseErrorsPanel } from './components/ParseErrorsPanel'
import { StatementList } from './components/StatementList'
import { SummaryPanel } from './components/SummaryPanel'
import { TransactionsTable } from './components/TransactionsTable'
import { UploadPanel } from './components/UploadPanel'
import { plural } from './format'
import { useStatement, type LoadStatus } from './useStatement'

export default function App() {
  const [statements, setStatements] = useState<StatementListItem[]>([])
  const [listStatus, setListStatus] = useState<LoadStatus>('loading')
  const [listError, setListError] = useState('')
  const [categories, setCategories] = useState<Categories>({ categories: [], kinds: [] })
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [notice, setNotice] = useState('')
  const { detail, summary, status, error, reload } = useStatement(selectedId)

  const refreshList = useCallback(async () => {
    try {
      setStatements(await listStatements())
      setListStatus('ready')
    } catch (caught) {
      setListError(errorMessage(caught))
      setListStatus('error')
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    listStatements()
      .then((items) => {
        if (cancelled) return
        setStatements(items)
        setListStatus('ready')
      })
      .catch((caught: unknown) => {
        if (cancelled) return
        setListError(errorMessage(caught))
        setListStatus('error')
      })
    getCategories()
      .then((loaded) => {
        if (!cancelled) setCategories(loaded)
      })
      .catch(() => undefined) // the editor then has no choices; the list error shows the cause
    return () => {
      cancelled = true
    }
  }, [])

  function select(id: number | null) {
    setSelectedId(id)
    setEditingId(null)
    setSaveError('')
    setNotice('')
  }

  function handleUploaded(statement: StatementDetail) {
    select(statement.id)
    void refreshList()
  }

  function openEditor(id: number | null) {
    setEditingId(id)
    setSaveError('')
    setNotice('')
  }

  async function handleSave(transaction: Transaction, body: CorrectionBody) {
    setSaving(true)
    setSaveError('')
    try {
      const result = await correctTransaction(transaction.id, body)
      setEditingId(null)
      setNotice(
        result.reclassified_count > 0
          ? `Saved. ${plural(result.reclassified_count, 'other row')} updated.`
          : 'Saved.',
      )
      await Promise.all([reload(), refreshList()])
    } catch (caught) {
      setSaveError(errorMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Statement Categorizer</h1>
        <p>Tax-time statement categorizer for a freelance developer</p>
      </header>
      <main>
        <UploadPanel onUploaded={handleUploaded} />
        <StatementList
          statements={statements}
          status={listStatus}
          error={listError}
          selectedId={selectedId}
          onSelect={select}
        />

        {selectedId === null && statements.length > 0 && (
          <p className="muted empty">Select a statement above to see its results.</p>
        )}
        {status === 'loading' && <p role="status">Loading statement…</p>}
        {status === 'error' && (
          <p role="alert" className="alert">
            {error}
          </p>
        )}

        {detail && (
          <>
            <div className="statement-head">
              <div>
                <h2>{detail.filename}</h2>
                <p className="muted">
                  {detail.account_type === 'card' ? 'Card statement' : 'Bank account statement'}
                </p>
              </div>
              <a className="button" href={exportUrl(detail.id)} download>
                Download categorized CSV
              </a>
            </div>
            <CountsBar statement={detail} />
            {notice && (
              <p role="status" className="notice">
                {notice}
              </p>
            )}
            <SummaryPanel summary={summary} status={status} />
            <TransactionsTable
              key={detail.id}
              transactions={detail.transactions}
              categories={categories.categories}
              kinds={categories.kinds}
              editingId={editingId}
              saving={saving}
              saveError={saveError}
              onEdit={openEditor}
              onSave={handleSave}
            />
            <ParseErrorsPanel errors={detail.parse_errors} skippedCount={detail.skipped_count} />
          </>
        )}
      </main>
    </div>
  )
}
