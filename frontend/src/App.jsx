import React, { useState, useEffect, useRef } from 'react';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  RefreshCw,
  Download,
  Search,
  DollarSign,
  PieChart,
  Cpu,
  Layers,
  Sparkles
} from './components/Icons';

const API_BASE = 'http://localhost:8000/api';

const CATEGORY_OPTIONS = [
  "Software & Subscriptions",
  "Office & Equipment",
  "Travel & Rideshare",
  "Meals & Entertainment",
  "Marketing & Advertising",
  "Professional & Banking Fees",
  "Utilities & Internet",
  "Gross Income",
  "Internal Transfer / Owner Draw",
  "Refund / Expense Offset",
  "Needs Review"
];

export default function App() {
  const [statementData, setStatementData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('ALL');
  const [toastMessage, setToastMessage] = useState(null);
  const fileInputRef = useRef(null);

  // Load sample statement on initial render so the app is immediately alive!
  useEffect(() => {
    loadSampleStatement();
  }, []);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const loadSampleStatement = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/statements/sample`);
      if (!res.ok) throw new Error('Failed to load sample statement');
      const data = await res.json();
      setStatementData(data);
      showToast('Loaded Freelancer Creative Business Statement (23 transactions with edge cases)');
    } catch (err) {
      console.error(err);
      showToast('Backend connection error. Make sure backend is running on port 8000.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/statements/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Upload failed');
      }
      const data = await res.json();
      setStatementData(data);
      showToast(`Successfully categorized ${file.name}`);
    } catch (err) {
      console.error(err);
      alert(err.message || 'Error uploading file');
    } finally {
      setLoading(false);
    }
  };

  const handleCategoryChange = async (txId, newCategory) => {
    try {
      const res = await fetch(`${API_BASE}/transactions/update-category`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transaction_id: txId,
          new_category: newCategory,
          apply_to_future: true,
        }),
      });

      if (!res.ok) throw new Error('Failed to update category');
      const updatedData = await res.json();
      setStatementData(updatedData);

      const updatedTx = updatedData.transactions.find((t) => t.id === txId);
      showToast(`Brain updated: Learned rule for "${updatedTx?.clean_merchant}" ➔ ${newCategory}`);
    } catch (err) {
      console.error(err);
      showToast('Failed to update transaction category');
    }
  };

  const handleExportCSV = () => {
    window.open(`${API_BASE}/statements/export`, '_blank');
  };

  const summary = statementData?.summary;
  const transactions = statementData?.transactions || [];

  // Filter transactions
  const filteredTransactions = transactions.filter((tx) => {
    // Search match
    const matchesSearch =
      tx.clean_merchant.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tx.raw_description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tx.category.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (selectedFilter === 'NEEDS_REVIEW') return tx.needs_review || tx.category === 'Needs Review';
    if (selectedFilter === 'SOFTWARE') return tx.category === 'Software & Subscriptions';
    if (selectedFilter === 'TRAVEL_MEALS')
      return tx.category === 'Travel & Rideshare' || tx.category === 'Meals & Entertainment';
    if (selectedFilter === 'INCOME_REFUND')
      return tx.category === 'Gross Income' || tx.category === 'Refund / Expense Offset';
    if (selectedFilter === 'TRANSFERS') return tx.category === 'Internal Transfer / Owner Draw';

    return true;
  });

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div
          style={{
            position: 'fixed',
            top: '1.25rem',
            right: '1.5rem',
            zIndex: 9999,
            background: '#1e293b',
            border: '1px solid #3b82f6',
            color: '#f8fafc',
            padding: '0.75rem 1.25rem',
            borderRadius: '8px',
            boxShadow: '0 10px 25px -5px rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.65rem',
            fontSize: '0.875rem',
            fontWeight: 500,
          }}
          className="fade-in"
        >
          <Sparkles size={18} color="#60a5fa" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Header Bar */}
      <header
        style={{
          background: '#0d111a',
          borderBottom: '1px solid var(--border-color)',
          padding: '0.85rem 1.5rem',
          position: 'sticky',
          top: 0,
          zIndex: 40,
        }}
      >
        <div
          style={{
            maxWidth: '1360px',
            margin: '0 auto',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            <div
              style={{
                width: '38px',
                height: '38px',
                background: 'linear-gradient(135deg, #2563eb, #7c3aed)',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
              }}
            >
              <Cpu size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <h1 style={{ fontSize: '1.15rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
                  TaxSort
                </h1>
                <span className="badge badge-purple" style={{ fontSize: '0.7rem' }}>
                  Deterministic Brain
                </span>
                <span className="badge badge-green" style={{ fontSize: '0.7rem' }}>
                  No External AI Models
                </span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                Statement Categorizer for Freelance Creative Designers & Consultants (Schedule C Tax Filing)
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button className="btn btn-secondary" onClick={loadSampleStatement} disabled={loading}>
              <RefreshCw size={15} className={loading ? 'spin' : ''} />
              Load Sample Statement
            </button>

            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".csv,.txt"
              style={{ display: 'none' }}
            />

            <button
              className="btn btn-primary"
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
            >
              <UploadCloud size={16} />
              Upload CSV
            </button>

            {statementData && (
              <button className="btn btn-success" onClick={handleExportCSV}>
                <Download size={16} />
                Export CSV
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="container" style={{ flex: 1 }}>
        {/* Active File Banner */}
        {statementData && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '1.5rem',
              padding: '0.75rem 1rem',
              background: '#131926',
              borderRadius: '8px',
              border: '1px solid #1f2a3f',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <FileText size={18} color="#60a5fa" />
              <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>Active Statement:</span>
              <code
                style={{
                  background: '#0d131f',
                  padding: '0.2rem 0.5rem',
                  borderRadius: '4px',
                  color: '#93c5fd',
                  fontSize: '0.8rem',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                {statementData.filename}
              </code>
              <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>
                ({transactions.length} rows processed)
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.8rem' }}>
              <span>
                Automation Rate:{' '}
                <strong style={{ color: '#34d399' }}>{summary?.accuracy_rate}%</strong>
              </span>
              <span>
                Needs Review:{' '}
                <strong style={{ color: summary?.needs_review_count > 0 ? '#fbbf24' : '#34d399' }}>
                  {summary?.needs_review_count}
                </strong>
              </span>
            </div>
          </div>
        )}

        {/* KPI Summary Cards */}
        {summary && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '1rem',
              marginBottom: '1.75rem',
            }}
          >
            {/* Total Income */}
            <div className="card">
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  color: 'var(--text-muted)',
                  fontSize: '0.8125rem',
                  fontWeight: 600,
                  marginBottom: '0.5rem',
                }}
              >
                <span>GROSS BUSINESS INCOME</span>
                <ArrowDownRight size={18} color="#10b981" />
              </div>
              <div style={{ fontSize: '1.65rem', fontWeight: 800, color: '#34d399' }}>
                ${summary.total_income.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.35rem' }}>
                Taxable client invoices & payouts
              </p>
            </div>

            {/* Net Tax Deductible Expenses */}
            <div
              className="card"
              style={{
                background: 'linear-gradient(180deg, #131b2e 0%, #111622 100%)',
                borderColor: '#2563eb',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  color: '#93c5fd',
                  fontSize: '0.8125rem',
                  fontWeight: 700,
                  marginBottom: '0.5rem',
                }}
              >
                <span>NET TAX DEDUCTIONS</span>
                <DollarSign size={18} color="#3b82f6" />
              </div>
              <div style={{ fontSize: '1.65rem', fontWeight: 800, color: '#60a5fa' }}>
                ${summary.net_tax_deductible_expenses.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </div>
              <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.35rem' }}>
                Schedule C eligible (50% meals + refunds offset)
              </p>
            </div>

            {/* Total Raw Expenses */}
            <div className="card">
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  color: 'var(--text-muted)',
                  fontSize: '0.8125rem',
                  fontWeight: 600,
                  marginBottom: '0.5rem',
                }}
              >
                <span>TOTAL SPEND / OUTFLOWS</span>
                <ArrowUpRight size={18} color="#f43f5e" />
              </div>
              <div style={{ fontSize: '1.65rem', fontWeight: 800, color: '#f1f5f9' }}>
                ${summary.total_expenses.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.35rem' }}>
                All gross operational card expenses
              </p>
            </div>

            {/* Internal Transfers Excluded */}
            <div className="card">
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  color: 'var(--text-muted)',
                  fontSize: '0.8125rem',
                  fontWeight: 600,
                  marginBottom: '0.5rem',
                }}
              >
                <span>TRANSFERS EXCLUDED</span>
                <Layers size={18} color="#94a3b8" />
              </div>
              <div style={{ fontSize: '1.65rem', fontWeight: 800, color: '#94a3b8' }}>
                ${summary.transfers_excluded.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.35rem' }}>
                Savings transfers, autopays (not spending)
              </p>
            </div>

            {/* Needs Review Counter */}
            <div
              className="card"
              style={{
                borderColor: summary.needs_review_count > 0 ? '#f59e0b' : 'var(--border-color)',
                cursor: 'pointer',
              }}
              onClick={() => setSelectedFilter('NEEDS_REVIEW')}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  color: summary.needs_review_count > 0 ? '#fbbf24' : 'var(--text-muted)',
                  fontSize: '0.8125rem',
                  fontWeight: 700,
                  marginBottom: '0.5rem',
                }}
              >
                <span>NEEDS REVIEW</span>
                <AlertTriangle size={18} color={summary.needs_review_count > 0 ? '#f59e0b' : '#64748b'} />
              </div>
              <div
                style={{
                  fontSize: '1.65rem',
                  fontWeight: 800,
                  color: summary.needs_review_count > 0 ? '#fbbf24' : '#34d399',
                }}
              >
                {summary.needs_review_count}
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.35rem' }}>
                {summary.needs_review_count > 0
                  ? 'Click to review & fix unclassified rows'
                  : 'All transactions categorized!'}
              </p>
            </div>
          </div>
        )}

        {/* Category Breakdown Chips */}
        {summary?.categories && summary.categories.length > 0 && (
          <div className="card" style={{ marginBottom: '1.75rem' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '1rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <PieChart size={18} color="#60a5fa" />
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>
                  Expense Category Distribution & Tax Deductibility
                </h3>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                Rule-based Schedule C breakdown
              </span>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
                gap: '0.75rem',
              }}
            >
              {summary.categories.map((cat, i) => (
                <div
                  key={i}
                  style={{
                    background: '#151c2a',
                    border: '1px solid #1f283d',
                    borderRadius: '8px',
                    padding: '0.75rem',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      marginBottom: '0.35rem',
                    }}
                  >
                    <span style={{ fontSize: '0.8125rem', fontWeight: 600 }}>{cat.category}</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 800 }}>
                      ${cat.total_amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span
                      className={`badge ${
                        cat.tax_status.includes('100%')
                          ? 'badge-green'
                          : cat.tax_status.includes('50%')
                          ? 'badge-amber'
                          : cat.tax_status.includes('Taxable')
                          ? 'badge-blue'
                          : cat.tax_status.includes('Offset')
                          ? 'badge-purple'
                          : 'badge-gray'
                      }`}
                      style={{ fontSize: '0.68rem', padding: '0.15rem 0.45rem' }}
                    >
                      {cat.tax_status}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      {cat.count} txns {cat.percentage_of_expenses > 0 ? `(${cat.percentage_of_expenses}%)` : ''}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Transactions Explorer & Table */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {/* Table Controls Bar */}
          <div
            style={{
              padding: '1.25rem',
              borderBottom: '1px solid var(--border-color)',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '1rem',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: '#131825',
            }}
          >
            {/* Filter Tabs */}
            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
              <button
                className={`btn ${selectedFilter === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ fontSize: '0.8125rem', padding: '0.45rem 0.85rem' }}
                onClick={() => setSelectedFilter('ALL')}
              >
                All ({transactions.length})
              </button>

              <button
                className={`btn ${
                  selectedFilter === 'NEEDS_REVIEW' ? 'btn-amber' : 'btn-secondary'
                }`}
                style={{ fontSize: '0.8125rem', padding: '0.45rem 0.85rem' }}
                onClick={() => setSelectedFilter('NEEDS_REVIEW')}
              >
                <AlertTriangle size={14} />
                Needs Review ({summary?.needs_review_count || 0})
              </button>

              <button
                className={`btn ${selectedFilter === 'SOFTWARE' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ fontSize: '0.8125rem', padding: '0.45rem 0.85rem' }}
                onClick={() => setSelectedFilter('SOFTWARE')}
              >
                Software & SaaS
              </button>

              <button
                className={`btn ${selectedFilter === 'TRAVEL_MEALS' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ fontSize: '0.8125rem', padding: '0.45rem 0.85rem' }}
                onClick={() => setSelectedFilter('TRAVEL_MEALS')}
              >
                Travel & Meals
              </button>

              <button
                className={`btn ${selectedFilter === 'INCOME_REFUND' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ fontSize: '0.8125rem', padding: '0.45rem 0.85rem' }}
                onClick={() => setSelectedFilter('INCOME_REFUND')}
              >
                Income & Refunds
              </button>

              <button
                className={`btn ${selectedFilter === 'TRANSFERS' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ fontSize: '0.8125rem', padding: '0.45rem 0.85rem' }}
                onClick={() => setSelectedFilter('TRANSFERS')}
              >
                Transfers
              </button>
            </div>

            {/* Search Input */}
            <div style={{ position: 'relative', width: '280px' }}>
              <Search
                size={16}
                color="#64748b"
                style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }}
              />
              <input
                type="text"
                placeholder="Search merchant, raw line..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  background: '#192131',
                  border: '1px solid #28354c',
                  borderRadius: '6px',
                  padding: '0.45rem 0.75rem 0.45rem 2rem',
                  color: 'white',
                  fontSize: '0.8125rem',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          {/* Table */}
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: '100px' }}>Date</th>
                  <th>Merchant / Description</th>
                  <th style={{ width: '120px' }}>Amount</th>
                  <th style={{ width: '250px' }}>Brain Category</th>
                  <th style={{ width: '140px' }}>Confidence</th>
                  <th>Rule / Decision Reason</th>
                </tr>
              </thead>
              <tbody>
                {filteredTransactions.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-dim)' }}>
                      No transactions matched the selected filter or search query.
                    </td>
                  </tr>
                ) : (
                  filteredTransactions.map((tx) => {
                    const isNeedsReview = tx.needs_review || tx.category === 'Needs Review';
                    const isIncome = tx.category === 'Gross Income';
                    const isRefund = tx.category === 'Refund / Expense Offset';
                    const isTransfer = tx.category === 'Internal Transfer / Owner Draw';

                    return (
                      <tr
                        key={tx.id}
                        className={isNeedsReview ? 'needs-review-row' : ''}
                      >
                        {/* Date */}
                        <td style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                          {tx.date}
                        </td>

                        {/* Merchant + Raw description */}
                        <td>
                          <div style={{ fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                            {tx.clean_merchant}
                            {tx.user_edited && (
                              <span className="badge badge-blue" style={{ fontSize: '0.65rem', padding: '0.1rem 0.35rem' }}>
                                User Edited
                              </span>
                            )}
                          </div>
                          <div
                            style={{
                              fontSize: '0.75rem',
                              color: 'var(--text-dim)',
                              fontFamily: 'var(--font-mono)',
                              marginTop: '2px',
                            }}
                          >
                            {tx.raw_description}
                          </div>
                        </td>

                        {/* Amount */}
                        <td>
                          <span
                            style={{
                              fontWeight: 700,
                              fontFamily: 'var(--font-mono)',
                              color: isIncome
                                ? '#34d399'
                                : isRefund
                                ? '#a78bfa'
                                : isTransfer
                                ? '#94a3b8'
                                : '#f1f5f9',
                            }}
                          >
                            {isIncome || isRefund ? '+' : '-'}$
                            {Math.abs(tx.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                          </span>
                        </td>

                        {/* Category Dropdown */}
                        <td>
                          <select
                            className={`category-select ${isNeedsReview ? 'needs-review-border' : ''}`}
                            value={tx.category}
                            onChange={(e) => handleCategoryChange(tx.id, e.target.value)}
                          >
                            {CATEGORY_OPTIONS.map((opt) => (
                              <option key={opt} value={opt}>
                                {opt}
                              </option>
                            ))}
                          </select>
                        </td>

                        {/* Confidence Score */}
                        <td>
                          <span
                            className={`badge ${
                              tx.confidence >= 0.90
                                ? 'badge-green'
                                : tx.confidence >= 0.70
                                ? 'badge-blue'
                                : 'badge-amber'
                            }`}
                          >
                            {tx.confidence >= 0.90 ? (
                              <CheckCircle2 size={12} />
                            ) : (
                              <AlertTriangle size={12} />
                            )}
                            {Math.round(tx.confidence * 100)}% Confidence
                          </span>
                        </td>

                        {/* Reason Note */}
                        <td>
                          <div style={{ fontSize: '0.8125rem', color: isNeedsReview ? '#fbbf24' : 'var(--text-muted)' }}>
                            {tx.review_reason}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid var(--border-color)',
          padding: '1.25rem 1.5rem',
          textAlign: 'center',
          fontSize: '0.8rem',
          color: 'var(--text-dim)',
          background: '#0d111a',
        }}
      >
        <p>
          TaxSort Technical Assessment Solution &bull; Built with FastAPI + React &bull; Developed by{' '}
          <strong style={{ color: '#f1f5f9' }}>Muhammad Usman (@usmhan123)</strong>
        </p>
      </footer>
    </div>
  );
}
