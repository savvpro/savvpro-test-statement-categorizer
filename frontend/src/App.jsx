import { useEffect, useMemo, useState } from 'react'
import { getCategories, reviewTransaction, uploadStatement } from './api.js'

const REVIEW = 'Needs Review'
const money = (v) => Number(v).toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export default function App() {
  const [categories, setCategories] = useState([])
  const [statement, setStatement] = useState(null)
  const [filter, setFilter] = useState('all')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getCategories().then(setCategories).catch((e) => setError(e.message))
  }, [])

  async function onUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setBusy(true)
    setError('')
    try {
      setStatement(await uploadStatement(file))
      setFilter('review')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
      e.target.value = ''
    }
  }

  async function onChange(tx, category) {
    try {
      setStatement(await reviewTransaction(statement.id, tx.id, category))
    } catch (err) {
      setError(err.message)
    }
  }

  const rows = useMemo(() => {
    if (!statement) return []
    return filter === 'review'
      ? statement.transactions.filter((t) => t.category === REVIEW)
      : statement.transactions
  }, [statement, filter])

  return (
    <main>
      <header>
        <h1>Statement Categorizer</h1>
        <p>For freelance designers: upload a card or bank statement (CSV) and get it sorted for tax time.</p>
      </header>

      <label className="upload">
        <input type="file" accept=".csv" onChange={onUpload} disabled={busy} />
        {busy ? 'Reading statement...' : 'Upload statement (.csv)'}
      </label>
      {error && <p className="error" role="alert">{error}</p>}

      {statement && (
        <>
          <Summary summary={statement.summary} />
          {statement.errors.length > 0 && (
            <details className="warn">
              <summary>{statement.errors.length} row(s) could not be read</summary>
              <ul>
                {statement.errors.map((e) => (
                  <li key={e.row}>Line {e.row}: {e.error}</li>
                ))}
              </ul>
            </details>
          )}
          <div className="tabs">
            <button className={filter === 'review' ? 'on' : ''} onClick={() => setFilter('review')}>
              Needs review ({statement.summary.needs_review})
            </button>
            <button className={filter === 'all' ? 'on' : ''} onClick={() => setFilter('all')}>
              All ({statement.transactions.length})
            </button>
          </div>
          <table>
            <thead>
              <tr>
                <th>Date</th><th>Description</th><th className="num">Amount</th><th>Category</th><th>Why</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id} className={t.category === REVIEW ? 'review' : ''}>
                  <td>{t.date}</td>
                  <td>
                    {t.description}
                    {t.is_refund && <span className="tag">refund</span>}
                  </td>
                  <td className={`num ${t.kind}`}>
                    {t.kind === 'credit' ? '+' : '-'}
                    {money(t.amount)}
                  </td>
                  <td>
                    <select value={t.category} onChange={(e) => onChange(t, e.target.value)}>
                      {categories.map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                    {t.category === REVIEW && t.suggested_category && (
                      <button className="link" onClick={() => onChange(t, t.suggested_category)}>
                        Use suggestion: {t.suggested_category}
                      </button>
                    )}
                  </td>
                  <td className="why">
                    {t.user_overridden ? 'Set by you.' : t.reason}{' '}
                    {!t.user_overridden && <small>({Math.round(t.confidence * 100)}%)</small>}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan="5" className="empty">Nothing needs review.</td>
                </tr>
              )}
            </tbody>
          </table>
        </>
      )}
    </main>
  )
}

function Summary({ summary }) {
  return (
    <section className="summary">
      <div className="cards">
        <div><span>Business expenses</span><strong>{money(summary.total_expenses)}</strong></div>
        <div><span>Client income</span><strong>{money(summary.total_income)}</strong></div>
        <div className={summary.ready_for_tax ? 'ok' : 'todo'}>
          <span>Status</span>
          <strong>{summary.ready_for_tax ? 'Ready for tax' : `${summary.needs_review} to review`}</strong>
        </div>
      </div>
      <table className="totals">
        <tbody>
          {Object.entries(summary.by_category).map(([c, v]) => (
            <tr key={c}><td>{c}</td><td className="num">{money(v)}</td></tr>
          ))}
        </tbody>
      </table>
      {!summary.ready_for_tax && <p className="hint">Totals exclude rows that still need review.</p>}
    </section>
  )
}
