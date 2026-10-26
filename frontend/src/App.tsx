import { useState, useCallback } from 'react'
import './App.css'

interface Transaction {
  date: string
  description: string
  amount: number
  category: string
  confidence: string
  reason: string
  normalized_description: string
  original_row?: number
}

interface CategorizeResponse {
  transactions: Transaction[]
  summary: Record<string, number>
  total_transactions: number
  needs_review_count: number
}

const CATEGORIES = [
  "Software & Subscriptions",
  "Cloud & Infrastructure",
  "Hardware & Equipment",
  "Travel & Transportation",
  "Meals & Entertainment",
  "Office & Co-working",
  "Professional Services",
  "Marketing & Advertising",
  "Bank Fees & Transfers",
  "Income",
  "Refunds & Chargebacks",
  "Personal",
  "Needs Review",
]

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value)
}

function App() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<CategorizeResponse | null>(null)
  const [filter, setFilter] = useState<'all' | 'needs_review'>('all')

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] || null
    setFile(selected)
    setError(null)
    setData(null)
  }

  const handleUpload = useCallback(async () => {
    if (!file) return

    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(`${API_BASE}/api/categorize`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Upload failed (${res.status})`)
      }

      const json: CategorizeResponse = await res.json()
      setData(json)
    } catch (err: any) {
      setError(err.message || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }, [file])

  const updateCategory = (index: number, newCategory: string) => {
    if (!data) return

    const updated = [...data.transactions]
    updated[index] = {
      ...updated[index],
      category: newCategory,
      confidence: 'high',
      reason: 'Manually corrected by user',
    }

    // Recalculate summary
    const summary: Record<string, number> = {}
    let needsReview = 0
    for (const tx of updated) {
      summary[tx.category] = (summary[tx.category] || 0) + tx.amount
      if (tx.category === 'Needs Review') needsReview++
    }

    setData({
      ...data,
      transactions: updated,
      summary: Object.fromEntries(
        Object.entries(summary).map(([k, v]) => [k, Math.round(v * 100) / 100])
      ),
      needs_review_count: needsReview,
    })
  }

  const visibleTransactions = data
    ? filter === 'needs_review'
      ? data.transactions.filter((t) => t.category === 'Needs Review')
      : data.transactions
    : []

  return (
    <div className="app">
      <header className="header">
        <h1>Statement Categorizer</h1>
        <p className="subtitle">
          For freelance software engineers · Rule-based · Tax-ready
        </p>
      </header>

      <section className="upload-section">
        <div className="upload-box">
          <label className="file-label">
            <input
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              disabled={loading}
            />
            <span>{file ? file.name : 'Choose a CSV statement'}</span>
          </label>
          <button
            className="btn primary"
            onClick={handleUpload}
            disabled={!file || loading}
          >
            {loading ? 'Categorizing…' : 'Categorize Statement'}
          </button>
        </div>
        {error && <div className="error">{error}</div>}
      </section>

      {data && (
        <>
          <section className="summary-section">
            <h2>Category Totals</h2>
            <div className="summary-grid">
              {Object.entries(data.summary)
                .sort((a, b) => a[0].localeCompare(b[0]))
                .map(([cat, total]) => (
                  <div
                    key={cat}
                    className={`summary-card ${cat === 'Needs Review' ? 'review' : ''}`}
                  >
                    <div className="cat-name">{cat}</div>
                    <div className={`cat-total ${total >= 0 ? 'positive' : 'negative'}`}>
                      {formatCurrency(total)}
                    </div>
                  </div>
                ))}
            </div>
            <div className="stats">
              <span>{data.total_transactions} transactions</span>
              <span className={data.needs_review_count > 0 ? 'warning' : ''}>
                {data.needs_review_count} need review
              </span>
            </div>
          </section>

          <section className="table-section">
            <div className="table-header">
              <h2>Transactions</h2>
              <div className="filters">
                <button
                  className={filter === 'all' ? 'active' : ''}
                  onClick={() => setFilter('all')}
                >
                  All
                </button>
                <button
                  className={filter === 'needs_review' ? 'active' : ''}
                  onClick={() => setFilter('needs_review')}
                >
                  Needs Review only
                </button>
              </div>
            </div>

            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Amount</th>
                    <th>Category</th>
                    <th>Confidence</th>
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleTransactions.map((tx) => {
                    const originalIndex = data.transactions.indexOf(tx)
                    return (
                      <tr
                        key={originalIndex}
                        className={tx.category === 'Needs Review' ? 'needs-review' : ''}
                      >
                        <td>{tx.date}</td>
                        <td className="desc" title={tx.description}>
                          {tx.description}
                        </td>
                        <td className={tx.amount >= 0 ? 'positive' : 'negative'}>
                          {formatCurrency(tx.amount)}
                        </td>
                        <td>
                          <select
                            value={tx.category}
                            onChange={(e) => updateCategory(originalIndex, e.target.value)}
                          >
                            {CATEGORIES.map((c) => (
                              <option key={c} value={c}>
                                {c}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <span className={`badge ${tx.confidence}`}>
                            {tx.confidence}
                          </span>
                        </td>
                        <td className="reason">{tx.reason}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      <footer className="footer">
        <p>
          The brain is 100% rule-based Python code. No large language model is used to decide categories.
        </p>
      </footer>
    </div>
  )
}

export default App
