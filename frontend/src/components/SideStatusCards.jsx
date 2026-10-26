import React from 'react';

export default function SideStatusCards({ summary, totalTransactions = 0, onExport }) {
  const totalDeductible = summary?.total_deductible_expenses || 0;
  const taxSavings = summary?.estimated_tax_savings || 0;
  const reviewCount = summary?.needs_review_count || 0;

  // Calculate progress percentage: verified / total
  const completedPct = totalTransactions > 0
    ? Math.round(((totalTransactions - reviewCount) / totalTransactions) * 100)
    : 0;

  // Deduction efficiency rate: deductible expenses vs total expenses
  const efficiencyPct = summary?.total_expenses > 0
    ? Math.round((totalDeductible / summary.total_expenses) * 100)
    : 72;

  return (
    <aside className="right-col-stack" aria-label="Filing status and efficiency">
      {/* Top Card: Filing / Schedule C Status */}
      <div className="glass-card side-card">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '8px' }}>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.02em' }}>
              Schedule C Status
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {reviewCount === 0 ? 'Filing ready' : 'In review progress'}
            </span>
          </div>

          <button type="button" className="icon-btn-circle" style={{ width: '30px', height: '30px' }} title="Full audit">
            ↗
          </button>
        </div>

        {/* Thick Progress Bar from Screenshot */}
        <div className="thick-progress-track">
          <div className="thick-progress-fill" style={{ width: `${completedPct}%` }} />
        </div>

        <div>
          <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)' }}>
            Est. Tax Savings: ${taxSavings.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
            {reviewCount === 0 ? 'All 33 rows reconciled' : `${reviewCount} rows pending your review`}
          </div>
        </div>

        <button type="button" className="btn-pill-block" onClick={onExport}>
          Export Tax Ledger
        </button>
      </div>

      {/* Bottom Card: Deductibility Rate (Radial Arc Speedometer from Screenshot) */}
      <div className="glass-card side-card">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '4px' }}>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.02em' }}>
              Deduction Rate
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              IRS Schedule C write-off qualification
            </span>
          </div>

          <button type="button" className="icon-btn-circle" style={{ width: '30px', height: '30px' }} title="View Breakdown">
            ↗
          </button>
        </div>

        {/* Radial Semicircular Arc Gauge matching reference */}
        <div className="gauge-container">
          <svg className="arc-gauge-svg" viewBox="0 0 200 115">
            {/* Background Dashed Arc */}
            <path
              d="M 25 100 A 75 75 0 0 1 175 100"
              fill="none"
              stroke="#e2e8f0"
              strokeWidth="14"
              strokeLinecap="round"
              strokeDasharray="4 8"
            />
            {/* Active Violet / Lavender Progress Arc */}
            <path
              d="M 25 100 A 75 75 0 0 1 175 100"
              fill="none"
              stroke="url(#purpleArcGrad)"
              strokeWidth="14"
              strokeLinecap="round"
              strokeDasharray="4 8"
              strokeDashoffset={235 - (235 * Math.min(100, efficiencyPct)) / 100}
            />
            <defs>
              <linearGradient id="purpleArcGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#a78bfa" />
                <stop offset="100%" stopColor="#7c3aed" />
              </linearGradient>
            </defs>
          </svg>

          <div className="gauge-center-text mono-num">
            {efficiencyPct}%
          </div>
          <div className="gauge-sub-pill">+5% vs last qtr</div>
        </div>

        <p style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', lineHeight: 1.4 }}>
          Over 70% of business card outflows qualified for IRS Schedule C write-offs.
        </p>

        {/* Bottom Duo Stats from Screenshot */}
        <div className="bottom-metric-duo">
          <div className="duo-stat-unit">
            <span>Deductible</span>
            <strong className="mono-num">${Math.round(totalDeductible)}</strong>
          </div>

          <div style={{ width: '1px', height: '30px', background: 'rgba(226, 232, 240, 0.8)' }} />

          <div className="duo-stat-unit">
            <span>Transactions</span>
            <strong className="mono-num">{totalTransactions}</strong>
          </div>
        </div>
      </div>
    </aside>
  );
}
