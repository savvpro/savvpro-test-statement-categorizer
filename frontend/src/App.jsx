import { useEffect, useMemo, useState } from 'react'
import './App.css'

const money = (amount, currency) => {
  const value = Number(amount)
  if (!Number.isFinite(value)) return `${amount} ${currency}`
  return `${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`
}

export default function App() {
  const [file, setFile] = useState(null)
  const [upload, setUpload] = useState(null)
  const [categories, setCategories] = useState([])
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const [dragging, setDragging] = useState(false)

  useEffect(() => {
    fetch('/api/categories')
      .then(async (r) => {
        if (!r.ok) throw new Error('Cannot load categories')
        return r.json()
      })
      .then(setCategories)
      .catch(() => setError('Backend unavailable. Start FastAPI on port 8000.'))
  }, [])

  const transactions = upload?.transactions ?? []
  const summary = upload?.summary

  const filtered = useMemo(() => {
    return transactions.filter((t) => {
      const search = `${t.description} ${t.category} ${t.currency}`.toLowerCase()
      if (!search.includes(query.toLowerCase())) return false
      if (filter === 'review') return t.needs_review
      if (filter === 'duplicate') return t.is_duplicate
      if (filter === 'invalid') return t.errors?.length > 0
      return true
    })
  }, [transactions, query, filter])

  const uploadFile = async (selected) => {
    if (!selected) return
    if (!selected.name.toLowerCase().endsWith('.csv')) {
      setError('Please select a CSV statement.')
      return
    }
    if (selected.size > 5 * 1024 * 1024) {
      setError('Maximum upload size is 5 MB.')
      return
    }

    setFile(selected)
    setError('')
    setBusy(true)

    try {
      const form = new FormData()
      form.append('file', selected)

      const response = await fetch('/api/uploads', {
        method: 'POST',
        body: form,
      })
      const data = await response.json()

      if (!response.ok) {
        throw new Error(typeof data.detail === 'string' ? data.detail : 'Upload failed.')
      }

      setUpload(data)
      setQuery('')
      setFilter('all')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const updateTransaction = async (transaction, changes) => {
    setEditing(transaction.id)
    setError('')

    try {
      const response = await fetch(
        `/api/uploads/${upload.upload_id}/transactions/${transaction.id}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(changes),
        },
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(typeof data.detail === 'string' ? data.detail : 'Update failed.')
      }

      // Reload to include all same-merchant corrections.
      const refreshed = await fetch(`/api/uploads/${upload.upload_id}`)
      if (!refreshed.ok) throw new Error('Could not refresh transactions.')
      setUpload(await refreshed.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setEditing(null)
    }
  }

  const exportCSV = async () => {
    if (!upload) return

    try {
      const response = await fetch(`/api/uploads/${upload.upload_id}/export.csv`)
      if (!response.ok) throw new Error('CSV export failed.')

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'categorized_statement.csv'
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">S</div>
          <div>
            <strong>SAVV Statement Intelligence</strong>
            <span>Smart transaction categorization</span>
          </div>
        </div>
        <span className="top-label">Financial Analysis Workspace</span>
      </header>

      <main className="container">
        <section className="hero">
          <div>
            <span className="eyebrow">STATEMENT CATEGORIZER</span>
            <h1>Understand every transaction.</h1>
            <p>Upload a bank statement, review intelligent categorization, and export clean financial records.</p>
          </div>
          <div className="hero-symbol">↗</div>
        </section>

        {error && (
          <div className="alert" role="alert">
            <span>{error}</span>
            <button onClick={() => setError('')}>Dismiss</button>
          </div>
        )}

        <section className="panel upload-panel">
          <div className="section-heading">
            <div>
              <h2>Upload statement</h2>
              <p>Start by selecting a CSV bank statement.</p>
            </div>
            <span className="pill">CSV · Max 5 MB</span>
          </div>

          <div
            className={`dropzone ${dragging ? 'dragging' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragging(false)
              uploadFile(e.dataTransfer.files[0])
            }}
          >
            <div className="upload-icon">↑</div>
            <h3>Drag and drop your statement</h3>
            <p>or choose a CSV file from your computer</p>
            <label className="primary-button file-label">
              Browse files
              <input
                type="file"
                accept=".csv,text/csv"
                disabled={busy}
                onChange={(e) => {
                  uploadFile(e.target.files[0])
                  e.target.value = ''
                }}
              />
            </label>
            {busy && <p className="processing">Processing your statement...</p>}
            {file && !busy && <p className="selected-file">Selected: {file.name}</p>}
          </div>
        </section>

        {summary && (
          <>
            <section className="overview">
              <div className="metric">
                <span>Total rows</span>
                <strong>{summary.total_rows}</strong>
                <small>Imported statement entries</small>
              </div>
              <div className="metric">
                <span>Needs review</span>
                <strong>{summary.needs_review_count}</strong>
                <small>Require manual verification</small>
              </div>
              <div className="metric">
                <span>Duplicates</span>
                <strong>{summary.duplicate_count}</strong>
                <small>Excluded from spending totals</small>
              </div>
              <div className="metric">
                <span>Invalid rows</span>
                <strong>{summary.invalid_count}</strong>
                <small>Unusable statement entries</small>
              </div>
            </section>

            <section className="currency-section">
              <div className="section-heading">
                <div>
                  <h2>Spending overview</h2>
                  <p>Currency totals are kept separate for accurate reporting.</p>
                </div>
              </div>
              <div className="currency-grid">
                {summary.currencies.map((item) => (
                  <div className="panel currency-card" key={item.currency}>
                    <span className="currency-label">{item.currency} · Total spending</span>
                    <strong>{money(item.total_spend, item.currency)}</strong>
                    <div className="category-breakdown">
                      {Object.entries(item.spend_by_category || {}).map(([category, amount]) => (
                        <div key={category}>
                          <span>{category}</span>
                          <b>{money(amount, item.currency)}</b>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="panel transactions-panel">
              <div className="section-heading">
                <div>
                  <h2>Transactions</h2>
                  <p>Review classifications and correct transactions when needed.</p>
                </div>
                <button className="primary-button" onClick={exportCSV}>↓ Export CSV</button>
              </div>

              <div className="toolbar">
                <input
                  className="search"
                  placeholder="Search transactions..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <select value={filter} onChange={(e) => setFilter(e.target.value)}>
                  <option value="all">All transactions</option>
                  <option value="review">Needs review</option>
                  <option value="duplicate">Duplicates</option>
                  <option value="invalid">Invalid rows</option>
                </select>
                <span className="result-count">{filtered.length} results</span>
              </div>

              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Description</th>
                      <th>Amount</th>
                      <th>Category</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((t) => (
                      <tr key={t.id}>
                        <td className="nowrap">{t.date || '—'}</td>
                        <td>
                          <strong className="description">{t.description || 'Unreadable entry'}</strong>
                          <small className="reason">{t.reason || ''}</small>
                          {!!t.errors?.length && <small className="error-text">{t.errors.join(', ')}</small>}
                        </td>
                        <td className="nowrap amount">{money(t.amount, t.currency)}</td>
                        <td>
                          <select
                            className="category-select"
                            value={t.category}
                            disabled={!!t.errors?.length || editing !== null}
                            onChange={(e) => updateTransaction(t, { category: e.target.value })}
                          >
                            {t.category === 'Needs Review' && <option value="Needs Review">Needs Review</option>}
                            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
                          </select>
                        </td>
                        <td>
                          <div className="badges">
                            {t.is_duplicate && <span className="status duplicate">Duplicate</span>}
                            {t.needs_review && <span className="status review">Needs review</span>}
                            {!!t.errors?.length && <span className="status invalid">Invalid</span>}
                            {t.user_corrected && <span className="status corrected">Corrected</span>}
                            {!t.is_duplicate && !t.needs_review && !t.errors?.length && !t.user_corrected &&
                              <span className="status ready">Categorized</span>}
                          </div>
                        </td>
                        <td>
                          {t.is_duplicate && !t.errors?.length && (
                            <button
                              className="text-button"
                              disabled={editing !== null}
                              onClick={() => updateTransaction(t, { keep_duplicate: true })}
                            >
                              Keep duplicate
                            </button>
                          )}
                          {editing === t.id && <small>Saving...</small>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {filtered.length === 0 && <div className="empty">No matching transactions found.</div>}
              </div>
            </section>
          </>
        )}

        <footer>Built for clarity, control, and trustworthy financial categorization.</footer>
      </main>
    </div>
  )
}
