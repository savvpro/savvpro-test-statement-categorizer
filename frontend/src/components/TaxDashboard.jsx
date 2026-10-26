import React from 'react';

export default function TaxDashboard({ summary, needsReviewCount }) {
  if (!summary) return null;

  const grossIncome = summary.gross_income || 0;
  const totalDeductible = summary.total_deductible_expenses || 0;
  const reviewCount = needsReviewCount ?? summary.needs_review_count ?? 0;
  const activeCategoriesCount = (summary.categories || []).filter((c) => c.transaction_count > 0).length;

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val || 0);
  };

  return (
    <section aria-label="Key Performance Indicators" className="metrics-row-4">
      {/* Card 1: Gross Income / Bank Inflow */}
      <div className="glass-card metric-stat-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="metric-icon-wrap">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <line x1="2" y1="10" x2="22" y2="10" />
            </svg>
          </div>
          <button
            type="button"
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '18px' }}
            title="Options"
          >
            ⋮
          </button>
        </div>
        <div className="metric-number-bold mono-num">{formatCurrency(grossIncome)}</div>
        <div className="metric-label-sub">Gross business revenue</div>
      </div>

      {/* Card 2: Uncategorized / Needs Review */}
      <div className="glass-card metric-stat-card">
        <div className="metric-icon-wrap metric-icon-purple">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
        </div>
        <div className="metric-number-bold mono-num">{reviewCount}</div>
        <div className="metric-label-sub">Uncategorized transactions</div>
      </div>

      {/* Card 3: Verified Tax Categories */}
      <div className="glass-card metric-stat-card">
        <div className="metric-icon-wrap">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
        </div>
        <div className="metric-number-bold mono-num">{activeCategoriesCount}</div>
        <div className="metric-label-sub">Active tax categories</div>
      </div>

      {/* Card 4: Tax Deductible Spending */}
      <div className="glass-card metric-stat-card">
        <div className="metric-icon-wrap">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
            <line x1="1" y1="10" x2="23" y2="10" />
          </svg>
        </div>
        <div className="metric-number-bold mono-num">{formatCurrency(totalDeductible)}</div>
        <div className="metric-label-sub">Eligible write-offs (Schedule C)</div>
      </div>
    </section>
  );
}
