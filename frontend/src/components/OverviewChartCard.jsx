import React from 'react';

export default function OverviewChartCard({ summary, transactions = [] }) {
  const totalDeductible = summary?.total_deductible_expenses || 0;
  const netProfit = summary?.net_taxable_profit || 0;

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(val || 0);
  };

  // Month bars modeled after reference: Jan, Feb, Mar, Apr, May (active), Jun, Jul, Aug, Sep
  const months = [
    { name: 'Jan', height: 45, isCurrent: false },
    { name: 'Feb', height: 65, isCurrent: false },
    { name: 'Mar', height: 40, isCurrent: false },
    { name: 'Apr', height: 50, isCurrent: false },
    { name: 'May', height: 90, isCurrent: true, tooltipDeductible: totalDeductible, tooltipNet: netProfit },
    { name: 'Jun', height: 35, isCurrent: false },
    { name: 'Jul', height: 55, isCurrent: false },
    { name: 'Aug', height: 30, isCurrent: false },
    { name: 'Sep', height: 48, isCurrent: false },
  ];

  return (
    <div className="glass-card overview-card">
      <div className="card-header-flex">
        <div>
          <h2 className="card-title-main">Deductions & Profit Overview</h2>
          <p className="card-subtext">Tax write-off overview from all business accounts</p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="dropdown-pill-btn">
            <span>📅 Current Quarter</span>
            <span style={{ fontSize: '10px' }}>▼</span>
          </div>

          <button type="button" className="icon-btn-circle" style={{ width: '32px', height: '32px' }} title="Full view">
            ↗
          </button>
        </div>
      </div>

      {/* Dual Stats Row */}
      <div className="chart-stats-row">
        <div className="stat-item-block">
          <div className="stat-item-label">
            <span>Tax Deductible</span>
            <span className="trend-pill trend-red">-11%</span>
          </div>
          <strong className="mono-num">{formatCurrency(totalDeductible)}</strong>
        </div>

        <div className="stat-item-block">
          <div className="stat-item-label">
            <span>Net Taxable Profit</span>
            <span className="trend-pill trend-green">+6%</span>
          </div>
          <strong className="mono-num">{formatCurrency(netProfit)}</strong>
        </div>
      </div>

      {/* Frosted Bar Pillars */}
      <div className="frosted-bars-wrap">
        {months.map((m) => (
          <div key={m.name} className="bar-col-item">
            {m.isCurrent && (
              <div className="bar-tooltip-popup">
                <div style={{ color: '#7c3aed' }}>● Write-offs: ${Math.round(totalDeductible)}</div>
                <div style={{ color: '#0f172a' }}>● Profit: ${Math.round(netProfit)}</div>
              </div>
            )}
            <div
              className={`bar-pillar ${m.isCurrent ? 'bar-active' : ''}`}
              style={{ height: `${m.height}%` }}
            />
            <span className="bar-x-label">{m.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
