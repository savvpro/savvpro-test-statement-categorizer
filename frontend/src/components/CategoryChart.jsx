import React from 'react';

export default function CategoryChart({ categories }) {
  if (!categories || categories.length === 0) return null;

  // Filter out categories with zero transactions
  const activeCategories = categories.filter((c) => c.transaction_count > 0);

  // Find max amount to calculate relative bar widths
  const maxAmount = Math.max(...activeCategories.map((c) => c.gross_amount), 1);

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val || 0);
  };

  return (
    <div className="glass-panel chart-panel">
      <div className="chart-header">
        <div>
          <h3 className="chart-title">Spending Breakdown by Tax Category</h3>
          <span className="chart-subtitle">IRS Schedule C Deductions Distribution</span>
        </div>
      </div>

      <div className="bars-container">
        {activeCategories.map((cat) => {
          const widthPct = Math.min(100, Math.max(4, (cat.gross_amount / maxAmount) * 100));
          return (
            <div key={cat.category} className="bar-row">
              <div className="bar-label" title={cat.category}>
                {cat.category}
              </div>

              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{
                    width: `${widthPct}%`,
                    backgroundColor: cat.color || '#3b82f6',
                  }}
                />
              </div>

              <div className="bar-values">
                <span className="mono-num">{formatCurrency(cat.gross_amount)}</span>
                <span className="bar-count">({cat.transaction_count} txn{cat.transaction_count > 1 ? 's' : ''})</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
