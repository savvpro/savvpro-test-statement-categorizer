
import { useState } from 'react'
import './App.css'

const API_URL = 'http://127.0.0.1:8000'

function App() {
  const [file, setFile] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [filename, setFilename] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleUpload(event) {
    event.preventDefault()

    if (!file) {
      setError('Please select a CSV file first.')
      return
    }

    setLoading(true)
    setError('')
    setTransactions([])

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`${API_URL}/categorize`, {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'Unable to process this CSV file.',
        )
      }

      setTransactions(data.transactions)
      setFilename(data.filename)
    } catch (err) {
      setError(
        err.message === 'Failed to fetch'
          ? 'Could not connect to the backend. Make sure FastAPI is running on port 8000.'
          : err.message,
      )
    } finally {
      setLoading(false)
    }
  }

  function updateCategory(index, category) {
    setTransactions((current) =>
      current.map((transaction, i) =>
        i === index ? { ...transaction, category } : transaction,
      ),
    )
  }

  const categories = [
    'Inventory and Supplies',
    'Shipping and Delivery',
    'Advertising and Marketing',
    'Platform Fees',
    'Software',
    'Utilities',
    'Refund',
    'Transfer - Not Spending',
    'Income',
    'Needs Review',
  ]

  const categoryTotals = transactions.reduce((totals, transaction) => {
    totals[transaction.category] =
      (totals[transaction.category] || 0) + transaction.amount
    return totals
  }, {})

  const reviewCount = transactions.filter(
    (transaction) => transaction.category === 'Needs Review',
  ).length

  return (
    <main className="app">
      <header className="header">
        <div>
          <p className="eyebrow">SMALL BUSINESS FINANCE</p>
          <h1>Statement Categorizer</h1>
          <p className="subtitle">
            Organize your e-commerce transactions and review categories
            before using them for bookkeeping.
          </p>
        </div>
        <span className="status">Rule-based categorization</span>
      </header>

      <section className="upload-card">
        <h2>Upload your statement</h2>
        <p>
          Choose a CSV file containing date, description, and amount columns.
        </p>

        <form onSubmit={handleUpload}>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => {
              setFile(event.target.files?.[0] || null)
              setError('')
            }}
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Categorizing...' : 'Upload and categorize'}
          </button>
        </form>

        <p className="helper">
          Categorization uses explicit rules. Unrecognized transactions are
          flagged for review.
        </p>

        {error && <p className="error">{error}</p>}
      </section>

      {transactions.length > 0 && (
        <>
          <section className="summary-grid">
            <article className="summary-card">
              <p>Transactions</p>
              <strong>{transactions.length}</strong>
            </article>
            <article className="summary-card">
              <p>Needs review</p>
              <strong>{reviewCount}</strong>
            </article>
            <article className="summary-card">
              <p>Categories used</p>
              <strong>
                {new Set(transactions.map((t) => t.category)).size}
              </strong>
            </article>
          </section>

          <section className="table-card">
            <div className="section-heading">
              <div>
                <h2>Transaction review</h2>
                <p className="helper">
                  File: {filename}. You can change a category before reviewing
                  the totals below.
                </p>
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
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((transaction, index) => (
                    <tr key={`${transaction.date}-${index}`}>
                      <td>{transaction.date}</td>
                      <td>{transaction.description}</td>
                      <td className="amount">
                        {transaction.amount.toLocaleString('en-US', {
                          style: 'currency',
                          currency: 'USD',
                        })}
                      </td>
                      <td>
                        <select
                          value={transaction.category}
                          onChange={(event) =>
                            updateCategory(index, event.target.value)
                          }
                          aria-label={`Category for ${transaction.description}`}
                        >
                          {categories.map((category) => (
                            <option key={category} value={category}>
                              {category}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="reason">{transaction.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="helper">
              Category changes update this page's totals only. They are not
              saved to a database or written back to the uploaded file.
            </p>
          </section>

          <section className="table-card">
            <h2>Category totals</h2>
            <div className="totals-list">
              {Object.entries(categoryTotals)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([category, total]) => (
                  <div className="total-row" key={category}>
                    <span>{category}</span>
                    <strong>
                      {total.toLocaleString('en-US', {
                        style: 'currency',
                        currency: 'USD',
                      })}
                    </strong>
                  </div>
                ))}
            </div>
            <p className="helper">
              Totals are net amounts by category, including refunds and
              transfers. Confirm your statement's currency before relying on
              these figures.
            </p>
          </section>
        </>
      )}

      {transactions.length === 0 && !loading && (
        <section className="empty-state">
          <h2>Your transactions will appear here</h2>
          <p>Upload a statement to review its categorized transactions.</p>
        </section>
      )}
    </main>
  )
}

export default App
