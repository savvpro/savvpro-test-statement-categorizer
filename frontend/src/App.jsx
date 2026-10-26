import { useMemo, useState } from 'react'
import { categorizeFile } from './api.js'
import UploadZone from './components/UploadZone.jsx'
import SummaryCards from './components/SummaryCards.jsx'
import ReviewQueue from './components/ReviewQueue.jsx'
import TransactionTable from './components/TransactionTable.jsx'
import { exportCsv } from './export.js'

/**
 * App state:
 *   result  -> CategorizeResponse from the backend (transactions, summary, meta, warnings)
 *   edits   -> { [transactionId]: categoryString } user fixes; the source of truth
 *              for totals is always (transactions + edits), recalculated live.
 */
export default function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [edits, setEdits] = useState({})

  async function handleFile(file) {
    setLoading(true)
    setError(null)
    try {
      const data = await categorizeFile(file)
      setResult(data)
      setEdits({})
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setResult(null)
    setEdits({})
    setError(null)
  }

  const effective = useMemo(() => {
    if (!result) return []
    return result.transactions.map((t) => {
      const overridden = Object.prototype.hasOwnProperty.call(edits, t.id)
      return {
        ...t,
        category: overridden ? edits[t.id] : t.category,
        needs_review: overridden ? false : t.needs_review,
      }
    })
  }, [result, edits])

  const summary = useMemo(() => computeSummary(effective), [effective])

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Statement Categorizer</h1>
          <p className="subtitle">
            Sorts a business credit-card statement for tax time — built for a freelance
            designer. Rule-based brain: when it is not sure, it says so.
          </p>
        </div>
        {result && (
          <button className="btn btn-ghost" onClick={reset}>
            ← Upload another statement
          </button>
        )}
      </header>

      {error && (
        <div className="banner banner-error" role="alert">
          <strong>Could not read that statement.</strong> {error}
        </div>
      )}

      {!result ? (
        <UploadZone onFile={handleFile} loading={loading} />
      ) : (
        <main className="results">
          <SummaryCards summary={summary} meta={result.meta} />

          {result.warnings.length > 0 && (
            <div className="banner banner-warn">
              <strong>Heads up while reading the file:</strong>
              <ul>
                {result.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          <ReviewQueue
            rows={effective.filter((t) => t.needs_review)}
            onAssign={(id, cat) => setEdits((e) => ({ ...e, [id]: cat }))}
          />

          <TransactionTable
            rows={effective}
            onAssign={(id, cat) => setEdits((e) => ({ ...e, [id]: cat }))}
          />

          <div className="actions">
            <button
              className="btn btn-primary"
              onClick={() => exportCsv(result.filename, effective)}
            >
              ⬇ Download categorized CSV
            </button>
            <span className="hint">
              {result.filename} · {summary.count} rows · totals update as you fix rows
            </span>
          </div>
        </main>
      )}
    </div>
  )
}

/** Mirrors backend bucketing so user edits recompute totals instantly. */
function computeSummary(rows) {
  const NON_SPENDING = new Set(['Transfers & Payments', 'Income', 'Refunds'])
  const s = {
    by_category: {},
    spending_total: 0,
    income_total: 0,
    refunds_total: 0,
    transfers_total: 0,
    review_count: 0,
    count: rows.length,
  }
  for (const t of rows) {
    const amount = Math.abs(t.amount)
    if (t.category === 'Income') s.income_total += amount
    else if (t.category === 'Refunds') s.refunds_total += amount
    else if (t.category === 'Transfers & Payments') s.transfers_total += amount
    else if (t.amount < 0 && t.category) {
      s.by_category[t.category] = (s.by_category[t.category] || 0) + amount
      s.spending_total += amount
    }
    if (t.needs_review) s.review_count += 1
  }
  s.spending_total = round2(s.spending_total)
  s.income_total = round2(s.income_total)
  s.refunds_total = round2(s.refunds_total)
  s.transfers_total = round2(s.transfers_total)
  for (const k of Object.keys(s.by_category)) s.by_category[k] = round2(s.by_category[k])
  return s
}

function round2(n) {
  return Math.round(n * 100) / 100
}
