import React from 'react';

const CATEGORY_COLORS = {
  Software: '#38bdf8',
  Travel: '#818cf8',
  Meals: '#fb923c',
  'Office Supplies': '#4ade80',
  'Other Business Expense': '#f472b6',
  'Needs Review': '#f59e0b',
  Income: '#10b981',
  Refund: '#2dd4bf',
  Transfer: '#94a3b8',
};

export default function SpendingBreakdown({ summary, selectedCategory, onSelectCategory }) {
  if (!summary || !summary.category_breakdown) return null;

  // Filter to expense categories with amount > 0
  const expenseCategories = summary.category_breakdown.filter((item) =>
    ['Software', 'Travel', 'Meals', 'Office Supplies', 'Other Business Expense'].includes(item.category) && item.total_amount > 0
  );

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(val);
  };

  return (
    <div className="spending-breakdown-card">
      <div className="spending-breakdown-title">
        <span>Expense Category Breakdown</span>
        <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
          Net Deductible: <strong>{formatCurrency(summary.net_expenses)}</strong> (Gross {formatCurrency(summary.total_expenses)} - Refunds {formatCurrency(summary.total_refunds)})
        </span>
      </div>

      {expenseCategories.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No categorized business expenses found in this statement yet.</p>
      ) : (
        <div className="spending-bars">
          {expenseCategories.map((item) => {
            const color = CATEGORY_COLORS[item.category] || '#94a3b8';
            const isSelected = selectedCategory === item.category;

            return (
              <div
                key={item.category}
                className="spending-row"
                style={{
                  cursor: 'pointer',
                  padding: '0.35rem 0.5rem',
                  borderRadius: '0.375rem',
                  backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.1)' : 'transparent',
                }}
                onClick={() => onSelectCategory(isSelected ? 'ALL' : item.category)}
                title={`Filter by ${item.category}`}
              >
                <div className="spending-row-header">
                  <span style={{ fontWeight: 500, color: isSelected ? 'var(--primary)' : '#fff' }}>
                    {item.category} ({item.count} items)
                  </span>
                  <span>
                    <strong>{formatCurrency(item.total_amount)}</strong>
                    <span style={{ color: 'var(--text-dim)', marginLeft: '0.5rem' }}>
                      ({item.percentage}%)
                    </span>
                  </span>
                </div>
                <div className="progress-track">
                  <div
                    className="progress-fill"
                    style={{
                      width: `${Math.min(100, Math.max(2, item.percentage))}%`,
                      backgroundColor: color,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
