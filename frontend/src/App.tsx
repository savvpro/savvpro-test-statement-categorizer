import React, { useState, useEffect, useMemo, useRef } from 'react'
import {
  FileSpreadsheet,
  FileText,
  AlertCircle,
  Check,
  ChevronDown,
  Download,
  Search,
  RotateCcw,
  Upload,
  ArrowDownRight,
  ArrowUpRight,
  Tag,
  Building2,
  FileCheck,
  Filter,
  CheckCircle2,
  HelpCircle,
} from 'lucide-react'

interface Transaction {
  id: number
  date: string
  description: string
  amount: string
  category: string
  confidence: string
  reason: string
  transaction_type: string
  include_in_expenses: boolean
  is_tax_deductible: boolean
}

interface CategoryBreakdownItem {
  category: string
  total: string
  count: number
}

interface StatementData {
  filename: string
  total_transactions: number
  categorized_count: number
  needs_review_count: number
  gross_expenses: string
  total_refunds: string
  net_expenses: string
  total_income: string
  net_profit: string
  category_breakdown: CategoryBreakdownItem[]
  transactions: Transaction[]
}

const DEFAULT_CATEGORIES = [
  "Software & Subscriptions",
  "Travel & Transit",
  "Meals (50% Deductible)",
  "Office Supplies & Equipment",
  "Advertising & Marketing",
  "Utilities & Internet",
  "Banking & Processing Fees",
  "Contract Labor & Professional Services",
  "Client Revenue",
  "Transfer",
  "Personal / Non-Deductible",
  "Needs Review",
]

const API_BASE = "http://localhost:8000"

export default function App() {
  const [data, setData] = useState<StatementData | null>(null)
  const [categories, setCategories] = useState<string[]>(DEFAULT_CATEGORIES)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState<boolean>(false)
  const [activeTab, setActiveTab] = useState<'all' | 'needs_review' | 'verified' | 'income'>('all')
  const [searchTerm, setSearchTerm] = useState<string>('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Fetch available tax categories from backend on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/categories`)
      .then((res) => (res.ok ? res.json() : null))
      .then((json) => {
        if (json?.categories) {
          setCategories(json.categories)
        }
      })
      .catch(() => {})
  }, [])

  // Upload Statement File
  const handleFileUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError('Please upload a valid CSV bank or credit card statement.')
      return
    }

    setLoading(true)
    setError(null)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`${API_BASE}/api/categorize`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errJson = await response.json().catch(() => null)
        throw new Error(errJson?.detail || `Upload failed (${response.statusText})`)
      }

      const result: StatementData = await response.json()
      setData(result)
      setActiveTab('all')
    } catch (err: any) {
      setError(err.message || 'Error processing statement file.')
    } finally {
      setLoading(false)
    }
  }

  // Load Demo Statement in 1 click
  const handleLoadSample = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/sample`)
      if (!res.ok) throw new Error('Could not load sample data.')
      const result: StatementData = await res.json()
      setData(result)
      setActiveTab('all')
    } catch (err: any) {
      setError(err.message || 'Failed to fetch demo statement.')
    } finally {
      setLoading(false)
    }
  }

  // Drag and Drop
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0])
    }
  }

  // User changes a category
  const handleCategoryChange = async (rowId: number, newCategory: string) => {
    if (!data) return

    const updatedTransactions = data.transactions.map((t) => {
      if (t.id === rowId) {
        const isExpense =
          newCategory !== 'Transfer' &&
          newCategory !== 'Client Revenue' &&
          newCategory !== 'Personal / Non-Deductible' &&
          newCategory !== 'Needs Review'

        return {
          ...t,
          category: newCategory,
          confidence: newCategory === 'Needs Review' ? 'low' : 'user_confirmed',
          reason:
            newCategory === 'Needs Review'
              ? 'Flagged for review by user.'
              : `Categorized as '${newCategory}' by user review.`,
          include_in_expenses: isExpense,
          is_tax_deductible: isExpense,
          transaction_type:
            newCategory === 'Client Revenue'
              ? 'income'
              : newCategory === 'Transfer'
              ? 'transfer'
              : t.transaction_type === 'refund'
              ? 'refund'
              : 'expense',
        }
      }
      return t
    })

    try {
      const res = await fetch(`${API_BASE}/api/recalculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transactions: updatedTransactions }),
      })

      if (res.ok) {
        const recalcData = await res.json()
        setData({
          ...data,
          ...recalcData,
          transactions: updatedTransactions,
        })
      } else {
        setData({
          ...data,
          transactions: updatedTransactions,
          needs_review_count: updatedTransactions.filter((x) => x.category === 'Needs Review').length,
          categorized_count: updatedTransactions.filter((x) => x.category !== 'Needs Review').length,
        })
      }
    } catch {
      setData({
        ...data,
        transactions: updatedTransactions,
        needs_review_count: updatedTransactions.filter((x) => x.category === 'Needs Review').length,
        categorized_count: updatedTransactions.filter((x) => x.category !== 'Needs Review').length,
      })
    }
  }

  // Export finalized CSV
  const handleExportCSV = () => {
    if (!data || !data.transactions.length) return

    const headers = [
      'Line',
      'Date',
      'Description',
      'Amount',
      'Tax Category',
      'Classification',
      'Schedule C Deductible',
      'Decision Trace',
    ]

    const rows = data.transactions.map((t) => [
      t.id,
      `"${t.date}"`,
      `"${t.description.replace(/"/g, '""')}"`,
      t.amount,
      `"${t.category}"`,
      t.transaction_type,
      t.is_tax_deductible ? 'YES' : 'NO',
      `"${t.reason.replace(/"/g, '""')}"`,
    ])

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n')

    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', `reconciled_${data.filename || 'statement'}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // Filter transactions
  const filteredTransactions = useMemo(() => {
    if (!data) return []
    return data.transactions.filter((item) => {
      const matchesSearch =
        searchTerm === '' ||
        item.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.amount.includes(searchTerm)

      if (!matchesSearch) return false

      if (activeTab === 'needs_review') return item.category === 'Needs Review'
      if (activeTab === 'verified') return item.category !== 'Needs Review' && item.include_in_expenses
      if (activeTab === 'income') return item.category === 'Client Revenue' || item.transaction_type === 'income' || item.category === 'Transfer'

      return true
    })
  }, [data, activeTab, searchTerm])

  const percentReconciled = useMemo(() => {
    if (!data || data.total_transactions === 0) return 0
    return Math.round((data.categorized_count / data.total_transactions) * 100)
  }, [data])

  return (
    <div className="app-shell">
      {/* Enterprise Top Navigation */}
      <header className="top-nav">
        <div className="nav-left">
          <div className="nav-brand">
            <div className="brand-badge">
              <FileSpreadsheet size={16} />
            </div>
            <span>LedgerLens</span>
          </div>

          <div className="nav-divider" />

          <div className="nav-context">
            <Building2 size={14} />
            <span>Freelance Creative</span>
            <span>•</span>
            <span className="context-tag">Schedule C (Form 1040)</span>
          </div>
        </div>

        <div className="nav-right">
          {data && (
            <>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  setData(null)
                  setError(null)
                }}
              >
                <RotateCcw size={13} />
                New Statement
              </button>

              <button className="btn btn-primary btn-sm" onClick={handleExportCSV}>
                <Download size={13} />
                Export CSV
              </button>
            </>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Error notification */}
        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '8px',
            padding: '0.85rem 1.25rem',
            color: '#f87171',
            fontSize: '0.85rem',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.65rem'
          }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {!data ? (
          /* Empty / Upload View */
          <div className="empty-view-wrapper">
            <div
              className={`upload-card ${dragActive ? 'is-dragover' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="upload-icon-box">
                <Upload size={24} />
              </div>

              <h2 className="upload-header">Upload bank or card statement</h2>
              <p className="upload-sub">
                Drop your CSV statement here or click to browse. The deterministic brain sorts every transaction for tax deductions without third-party AI models.
              </p>

              <input
                type="file"
                ref={fileInputRef}
                accept=".csv"
                style={{ display: 'none' }}
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileUpload(e.target.files[0])
                  }
                }}
              />

              <div className="upload-actions-row" onClick={(e) => e.stopPropagation()}>
                <button
                  className="btn btn-primary"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={loading}
                >
                  <FileText size={15} />
                  {loading ? 'Processing...' : 'Select CSV File'}
                </button>

                <button
                  className="btn btn-secondary"
                  onClick={handleLoadSample}
                  disabled={loading}
                >
                  <FileCheck size={15} />
                  Load Sample Statement
                </button>
              </div>

              <div className="upload-specs">
                <span>Standard CSV headers</span>
                <span>•</span>
                <span>Heuristic rule-based brain</span>
                <span>•</span>
                <span>Max 5 MB</span>
              </div>
            </div>
          </div>
        ) : (
          /* Reconciled Statement Dashboard */
          <>
            {/* Reconciliation Progress Bar */}
            <div className="progress-strip">
              <div className="progress-info">
                <div className="progress-label">
                  <strong>Reconciliation Status:</strong> {data.categorized_count} of {data.total_transactions} items sorted ({percentReconciled}%)
                </div>
                <div className="progress-bar-bg">
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${percentReconciled}%` }}
                  />
                </div>
              </div>

              {data.needs_review_count > 0 ? (
                <button
                  className="btn btn-secondary btn-sm"
                  style={{ borderColor: 'rgba(245, 158, 11, 0.4)', color: '#fbbf24' }}
                  onClick={() => setActiveTab('needs_review')}
                >
                  <AlertCircle size={13} />
                  Review {data.needs_review_count} Unresolved Item{data.needs_review_count > 1 ? 's' : ''}
                </button>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#10b981', fontSize: '0.825rem', fontWeight: 500 }}>
                  <CheckCircle2 size={15} />
                  <span>All transactions verified</span>
                </div>
              )}
            </div>

            {/* Financial Metrics Row */}
            <div className="metrics-row">
              <div className="metric-card net-deductions-card">
                <div className="metric-top">
                  <span className="metric-label">Net Tax Deductions</span>
                  <ArrowDownRight size={18} className="metric-icon" style={{ color: '#10b981' }} />
                </div>
                <div className="metric-value" style={{ color: '#10b981' }}>
                  ${data.net_expenses}
                </div>
                <div className="metric-desc">Gross expenses minus refunds & credits</div>
              </div>

              <div className="metric-card">
                <div className="metric-top">
                  <span className="metric-label">Gross Deductible Outlays</span>
                  <ArrowDownRight size={18} className="metric-icon" />
                </div>
                <div className="metric-value">${data.gross_expenses}</div>
                <div className="metric-desc">Eligible Schedule C expense lines</div>
              </div>

              <div className="metric-card">
                <div className="metric-top">
                  <span className="metric-label">Refunds & Reversals</span>
                  <RotateCcw size={18} className="metric-icon" style={{ color: '#06b6d4' }} />
                </div>
                <div className="metric-value" style={{ color: '#06b6d4' }}>
                  -${data.total_refunds}
                </div>
                <div className="metric-desc">Credited against expenses (not income)</div>
              </div>

              <div className="metric-card">
                <div className="metric-top">
                  <span className="metric-label">Client Revenue</span>
                  <ArrowUpRight size={18} className="metric-icon" style={{ color: '#3b82f6' }} />
                </div>
                <div className="metric-value">${data.total_income}</div>
                <div className="metric-desc">Gross 1099 self-employment receipts</div>
              </div>
            </div>

            {/* Category Breakdown Panel */}
            {data.category_breakdown && data.category_breakdown.length > 0 && (
              <div className="breakdown-card">
                <div className="breakdown-header">
                  <div className="breakdown-title">
                    <Tag size={15} color="#94a3b8" />
                    <span>Schedule C Category Totals</span>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                    Aggregated from verified rows
                  </span>
                </div>
                <div className="breakdown-grid">
                  {data.category_breakdown.map((item) => (
                    <div key={item.category} className="breakdown-item">
                      <span className="breakdown-item-name" title={item.category}>
                        {item.category}
                      </span>
                      <span className="breakdown-item-val">${item.total}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Table Toolbar */}
            <div className="table-toolbar">
              <div className="view-tabs">
                <button
                  className={`view-tab ${activeTab === 'all' ? 'active' : ''}`}
                  onClick={() => setActiveTab('all')}
                >
                  All Items
                  <span className="tab-pill">{data.total_transactions}</span>
                </button>

                <button
                  className={`view-tab ${activeTab === 'needs_review' ? 'active' : ''}`}
                  onClick={() => setActiveTab('needs_review')}
                >
                  Needs Review
                  <span
                    className={`tab-pill ${
                      data.needs_review_count > 0 ? 'tab-pill-warning' : ''
                    }`}
                  >
                    {data.needs_review_count}
                  </span>
                </button>

                <button
                  className={`view-tab ${activeTab === 'verified' ? 'active' : ''}`}
                  onClick={() => setActiveTab('verified')}
                >
                  Verified Expenses
                  <span className="tab-pill">
                    {data.transactions.filter((t) => t.include_in_expenses).length}
                  </span>
                </button>

                <button
                  className={`view-tab ${activeTab === 'income' ? 'active' : ''}`}
                  onClick={() => setActiveTab('income')}
                >
                  Income & Transfers
                  <span className="tab-pill">
                    {data.transactions.filter((t) => !t.include_in_expenses).length}
                  </span>
                </button>
              </div>

              <div className="toolbar-actions">
                <div className="search-box">
                  <Search size={14} color="#64748b" />
                  <input
                    type="text"
                    placeholder="Search transactions..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
              </div>
            </div>

            {/* Financial Ledger Data Table */}
            <div className="table-container">
              <div className="table-scroller">
                <table className="fin-table">
                  <thead>
                    <tr>
                      <th style={{ width: '40px' }}>#</th>
                      <th style={{ width: '100px' }}>Date</th>
                      <th>Merchant & Rule Audit Trace</th>
                      <th style={{ width: '240px' }}>Tax Category</th>
                      <th style={{ width: '130px' }}>Status</th>
                      <th style={{ width: '120px', textAlign: 'right' }}>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTransactions.length === 0 ? (
                      <tr>
                        <td
                          colSpan={6}
                          style={{
                            textAlign: 'center',
                            padding: '3rem 1rem',
                            color: 'var(--text-tertiary)',
                          }}
                        >
                          No transactions found matching current filters.
                        </td>
                      </tr>
                    ) : (
                      filteredTransactions.map((tx) => {
                        const isReview = tx.category === 'Needs Review'
                        const num = parseFloat(tx.amount)
                        const isCredit = num > 0
                        const isRefund = tx.transaction_type === 'refund'
                        const isTransfer = tx.transaction_type === 'transfer'

                        return (
                          <tr
                            key={tx.id}
                            className={isReview ? 'needs-review-row' : ''}
                          >
                            <td className="col-id">{tx.id}</td>
                            <td className="col-date">{tx.date}</td>
                            <td>
                              <div className="col-merchant">
                                <span className="merchant-name">
                                  {tx.description}
                                </span>
                                <span className="merchant-meta">
                                  <span>{tx.reason}</span>
                                </span>
                              </div>
                            </td>
                            <td className="col-category">
                              <div className="category-input-wrapper">
                                <select
                                  className={`category-dropdown ${
                                    isReview ? 'is-review' : ''
                                  }`}
                                  value={tx.category}
                                  onChange={(e) =>
                                    handleCategoryChange(tx.id, e.target.value)
                                  }
                                >
                                  {categories.map((c) => (
                                    <option key={c} value={c}>
                                      {c}
                                    </option>
                                  ))}
                                </select>
                                <ChevronDown
                                  size={13}
                                  className="dropdown-chevron"
                                />
                              </div>
                            </td>
                            <td>
                              {isReview ? (
                                <span className="status-pill status-review">
                                  <AlertCircle size={11} />
                                  Review Needed
                                </span>
                              ) : tx.confidence === 'user_confirmed' ? (
                                <span className="status-pill status-user">
                                  <Check size={11} />
                                  User Confirmed
                                </span>
                              ) : isTransfer ? (
                                <span className="status-pill status-transfer">
                                  Transfer
                                </span>
                              ) : (
                                <span className="status-pill status-verified">
                                  <Check size={11} />
                                  Verified
                                </span>
                              )}
                            </td>
                            <td className="col-amount">
                              <span
                                className={
                                  isRefund
                                    ? 'amount-refund'
                                    : isCredit
                                    ? 'amount-credit'
                                    : 'amount-debit'
                                }
                              >
                                {isRefund
                                  ? `+$${Math.abs(num).toFixed(2)}`
                                  : isCredit
                                  ? `+$${Math.abs(num).toFixed(2)}`
                                  : `-$${Math.abs(num).toFixed(2)}`}
                              </span>
                            </td>
                          </tr>
                        )
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {/* Table Footer Bar */}
              <div className="table-footer-bar">
                <span>
                  Showing {filteredTransactions.length} of {data.total_transactions} items from {data.filename}
                </span>

                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                  <button className="btn btn-secondary btn-sm" onClick={handleExportCSV}>
                    <Download size={13} />
                    Export CSV
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
