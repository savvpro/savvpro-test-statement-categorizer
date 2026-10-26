import React, { useState } from 'react';

const ALL_CATEGORIES = [
  'Software',
  'Travel',
  'Meals',
  'Office Supplies',
  'Income',
  'Refund',
  'Transfer',
  'Other Business Expense',
  'Needs Review',
];

export default function TransactionTable({ transactions, onCategoryChange, updatingTxId }) {
  const formatCurrency = (amount) => {
    const isPositive = amount > 0;
    const formatted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(Math.abs(amount));

    if (isPositive) {
      return <span className="text-success">+{formatted}</span>;
    }
    return <span>-{formatted}</span>;
  };

  const getStatusBadge = (tx) => {
    if (tx.status === 'needs_review' || tx.category === 'Needs Review') {
      return (
        <span className="badge badge-warning" title="Confidence is low; tax deduction requires confirmation">
          ⚠️ Needs Review
        </span>
      );
    }
    if (tx.status === 'manual' || tx.is_reviewed) {
      return (
        <span className="badge badge-purple" title="Confirmed or updated by user">
          ✓ Manual Fix
        </span>
      );
    }
    return (
      <span className="badge badge-neutral" title={`Categorized with confidence ${(tx.confidence * 100).toFixed(0)}%`}>
        ⚡ Auto ({Math.round(tx.confidence * 100)}%)
      </span>
    );
  };

  if (!transactions || transactions.length === 0) {
    return (
      <div className="empty-state">
        <h3>No Transactions Match</h3>
        <p>No transactions match your current search and filter criteria.</p>
      </div>
    );
  }

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th style={{ width: '110px' }}>Date</th>
            <th>Description & Audit Rule</th>
            <th style={{ width: '130px', textAlign: 'right' }}>Amount</th>
            <th style={{ width: '210px' }}>Category</th>
            <th style={{ width: '140px' }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((tx) => {
            const isNeedsReview = tx.category === 'Needs Review' || tx.status === 'needs_review';
            const isUpdating = updatingTxId === tx.id;

            return (
              <tr
                key={tx.id}
                className={isNeedsReview ? 'row-needs-review' : ''}
              >
                <td style={{ whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>
                  {tx.date}
                </td>
                <td>
                  <div className="tx-desc-main">{tx.description}</div>
                  <div className="tx-rule-sub" title={tx.matched_rule}>
                    💡 {tx.matched_rule}
                  </div>
                </td>
                <td style={{ textAlign: 'right', fontWeight: 600 }}>
                  {formatCurrency(tx.amount)}
                </td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <select
                      className="category-select"
                      value={tx.category}
                      disabled={isUpdating}
                      onChange={(e) => onCategoryChange(tx.id, e.target.value)}
                      style={
                        isNeedsReview
                          ? { borderColor: 'var(--warning)', color: '#fde68a' }
                          : {}
                      }
                    >
                      {ALL_CATEGORIES.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat}
                        </option>
                      ))}
                    </select>
                    {isUpdating && <span className="spinner" style={{ width: '14px', height: '14px' }}></span>}
                  </div>
                </td>
                <td>{getStatusBadge(tx)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
