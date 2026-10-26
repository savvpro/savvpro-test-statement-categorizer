import React from 'react';

export default function TopNavbar({
  activeTab = 'Dashboard',
  onTabChange,
  onReset,
  hasData = false,
  needsReviewCount = 0,
  onExportCsv,
}) {
  const tabs = [
    { id: 'Dashboard', label: 'Dashboard' },
    { id: 'Needs Review', label: 'Needs Review', badge: needsReviewCount > 0 ? needsReviewCount : null },
    { id: 'Deductions', label: 'Deductions' },
    { id: 'All Transactions', label: 'All Transactions' },
  ];

  return (
    <header className="top-appbar">
      {/* Brand Section Left */}
      <div className="brand-section">
        <div className="brand-icon-spiral">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 3a9 9 0 0 1 9 9 9 9 0 0 1-9 9" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        </div>
        <div>
          <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.02em' }}>
            TaxFlow
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>
            Schedule C Statement Categorizer
          </div>
        </div>
      </div>

      {/* Center Capsule Tabs (Only when data is loaded, or simplified) */}
      {hasData ? (
        <nav className="nav-pill-capsule" aria-label="Dashboard Navigation">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`nav-pill-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => onTabChange && onTabChange(tab.id)}
            >
              <span>{tab.label}</span>
              {tab.badge !== null && tab.badge !== undefined && (
                <span
                  style={{
                    marginLeft: '6px',
                    padding: '1px 6px',
                    fontSize: '10px',
                    borderRadius: 'var(--radius-pill)',
                    background: activeTab === tab.id ? 'var(--accent-amber)' : 'var(--accent-amber-soft)',
                    color: activeTab === tab.id ? '#ffffff' : 'var(--accent-amber)',
                    fontWeight: 700,
                  }}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </nav>
      ) : (
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>
          Freelance Software Engineering & Tech Consulting Edition
        </div>
      )}

      {/* Right Actions */}
      <div className="topbar-right-utils">
        {hasData && (
          <>
            <button
              type="button"
              className="btn-pill-primary"
              style={{ padding: '6px 14px', fontSize: '12px' }}
              onClick={onExportCsv}
              title="Download categorized CSV ledger"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Export CSV
            </button>

            <button
              type="button"
              className="btn-pill-glass"
              onClick={onReset}
              title="Import a different CSV statement"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              Upload New
            </button>
          </>
        )}

        {/* User Pill Badge */}
        <div className="avatar-badge-wrap" title="Freelance Tax Profile">
          <div className="user-avatar-circle">SC</div>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-main)', paddingRight: '4px' }}>
            Consultant
          </span>
        </div>
      </div>
    </header>
  );
}
