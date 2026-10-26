import React from 'react';

export default function SummaryCards({ summary }) {
  if (!summary) return null;

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(val);
  };

  return (
    <div className="summary-grid">
      {/* 1. Total Transactions */}
      <div className="summary-card">
        <div className="summary-card-header">
          <span>Transactions</span>
          <span>📊</span>
        </div>
        <div className="summary-card-value">{summary.total_transactions}</div>
        <div className="summary-card-footer">Rows processed from statement</div>
      </div>

      {/* 2. Total Income */}
      <div className="summary-card">
        <div className="summary-card-header">
          <span>Gross Income</span>
          <span>💰</span>
        </div>
        <div className="summary-card-value text-success">
          {formatCurrency(summary.total_income)}
        </div>
        <div className="summary-card-footer">Client payments & revenues</div>
      </div>

      {/* 3. Total Expenses */}
      <div className="summary-card">
        <div className="summary-card-header">
          <span>Gross Expenses</span>
          <span>💳</span>
        </div>
        <div className="summary-card-value text-danger">
          {formatCurrency(summary.total_expenses)}
        </div>
        <div className="summary-card-footer">Tax deductible business costs</div>
      </div>

      {/* 4. Needs Review Alert Card */}
      <div className="summary-card" style={summary.needs_review_count > 0 ? { borderColor: 'var(--warning)' } : {}}>
        <div className="summary-card-header">
          <span>Needs Review</span>
          <span>⚠️</span>
        </div>
        <div className={`summary-card-value ${summary.needs_review_count > 0 ? 'text-warning' : 'text-success'}`}>
          {summary.needs_review_count}
        </div>
        <div className="summary-card-footer">
          {summary.needs_review_count > 0
            ? 'Action required for tax filing'
            : 'All transactions categorized!'}
        </div>
      </div>

      {/* 5. Refunds & Reversals */}
      <div className="summary-card">
        <div className="summary-card-header">
          <span>Refunds Received</span>
          <span>🔄</span>
        </div>
        <div className="summary-card-value text-primary">
          {formatCurrency(summary.total_refunds)}
        </div>
        <div className="summary-card-footer">Offsets expenses; not taxable income</div>
      </div>

      {/* 6. Transfers (Excluded) */}
      <div className="summary-card">
        <div className="summary-card-header">
          <span>Transfers (Neutral)</span>
          <span>🔁</span>
        </div>
        <div className="summary-card-value text-muted" style={{ color: '#cbd5e1' }}>
          {formatCurrency(summary.transfers_total)}
        </div>
        <div className="summary-card-footer">
          {summary.transfers_count} transfer(s) excluded from totals
        </div>
      </div>
    </div>
  );
}
