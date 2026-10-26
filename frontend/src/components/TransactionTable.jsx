import React, { useState, useMemo } from 'react';
import { Search, AlertTriangle, CheckCircle, HelpCircle, ArrowUpRight, ArrowDownLeft, RefreshCcw, Edit2 } from 'lucide-react';

export default function TransactionTable({
  transactions,
  onReviewClick,
  activeFilterTab,
  onTabChange,
  allCategories,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');

  const needsReviewCount = useMemo(() => {
    return transactions.filter((t) => t.needs_review).length;
  }, [transactions]);

  const filteredTransactions = useMemo(() => {
    return transactions.filter((tx) => {
      // Tab filter
      if (activeFilterTab === 'NEEDS_REVIEW' && !tx.needs_review) return false;
      if (activeFilterTab === 'EXPENSES' && (!tx.is_expense || tx.needs_review)) return false;
      if (activeFilterTab === 'INCOME_TRANSFERS' && tx.is_expense) return false;

      // Category filter dropdown
      if (selectedCategory !== 'ALL' && tx.category !== selectedCategory) return false;

      // Text search
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const matchesDesc = tx.raw_description.toLowerCase().includes(q);
        const matchesMerchant = (tx.cleaned_merchant || '').toLowerCase().includes(q);
        const matchesCat = tx.category.toLowerCase().includes(q);
        const matchesAmt = tx.amount.toString().includes(q);
        return matchesDesc || matchesMerchant || matchesCat || matchesAmt;
      }

      return true;
    });
  }, [transactions, activeFilterTab, selectedCategory, searchTerm]);

  const formatCurrency = (amt) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amt || 0);
  };

  return (
    <div className="glass-panel" style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Controls: Tabs & Search */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        {/* Filter Tabs */}
        <div style={{ display: 'flex', gap: 6, background: 'rgba(0, 0, 0, 0.25)', padding: 4, borderRadius: 10 }}>
          <button
            onClick={() => onTabChange('ALL')}
            className={`btn btn-sm ${activeFilterTab === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.78rem', border: 'none' }}
          >
            All ({transactions.length})
          </button>

          <button
            onClick={() => onTabChange('NEEDS_REVIEW')}
            className={`btn btn-sm ${activeFilterTab === 'NEEDS_REVIEW' ? 'btn-amber' : 'btn-secondary'}`}
            style={{ fontSize: '0.78rem', border: 'none', display: 'flex', alignItems: 'center', gap: 6 }}
          >
            {needsReviewCount > 0 && <AlertTriangle size={13} color="#f59e0b" />}
            <span>Needs Review</span>
            <span style={{
              background: needsReviewCount > 0 ? '#ef4444' : 'rgba(255,255,255,0.1)',
              color: '#fff',
              fontSize: '0.68rem',
              fontWeight: 700,
              padding: '1px 6px',
              borderRadius: 10,
            }}>
              {needsReviewCount}
            </span>
          </button>

          <button
            onClick={() => onTabChange('EXPENSES')}
            className={`btn btn-sm ${activeFilterTab === 'EXPENSES' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.78rem', border: 'none' }}
          >
            Deductible Expenses
          </button>

          <button
            onClick={() => onTabChange('INCOME_TRANSFERS')}
            className={`btn btn-sm ${activeFilterTab === 'INCOME_TRANSFERS' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.78rem', border: 'none' }}
          >
            Income & Transfers
          </button>
        </div>

        {/* Search & Category Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          {/* Search Input */}
          <div style={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
          }}>
            <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: 10 }} />
            <input
              type="text"
              placeholder="Search transactions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-primary)',
                padding: '7px 12px 7px 32px',
                fontSize: '0.82rem',
                outline: 'none',
                width: 200,
              }}
            />
          </div>

          {/* Category Dropdown */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              padding: '7px 12px',
              fontSize: '0.82rem',
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            <option value="ALL" style={{ background: '#111622' }}>All Categories</option>
            {allCategories.map((c) => (
              <option key={c.name} value={c.name} style={{ background: '#111622' }}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Transaction Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.84rem' }}>
          <thead>
            <tr style={{
              borderBottom: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
              fontSize: '0.75rem',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}>
              <th style={{ padding: '12px 14px' }}>Date</th>
              <th style={{ padding: '12px 14px' }}>Description & Cleaned Merchant</th>
              <th style={{ padding: '12px 14px', textAlign: 'right' }}>Amount</th>
              <th style={{ padding: '12px 14px' }}>Brain Category</th>
              <th style={{ padding: '12px 14px' }}>Confidence</th>
              <th style={{ padding: '12px 14px' }}>Schedule C Line</th>
              <th style={{ padding: '12px 14px' }}>The Brain's Reasoning</th>
              <th style={{ padding: '12px 14px', textAlign: 'center' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredTransactions.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No transactions match the selected filters.
                </td>
              </tr>
            ) : (
              filteredTransactions.map((tx) => {
                const isNeedsReview = tx.needs_review;
                const isPositive = tx.amount > 0;
                const isRefund = tx.category.includes('Refund');

                return (
                  <tr
                    key={tx.id}
                    style={{
                      borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                      background: isNeedsReview ? 'rgba(245, 158, 11, 0.03)' : 'transparent',
                      transition: 'background 0.15s ease',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)')}
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background = isNeedsReview ? 'rgba(245, 158, 11, 0.03)' : 'transparent')
                    }
                  >
                    {/* Date */}
                    <td style={{ padding: '12px 14px', whiteSpace: 'nowrap', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                      {tx.date || '—'}
                    </td>

                    {/* Description & Clean Merchant */}
                    <td style={{ padding: '12px 14px', maxWidth: 280 }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)', wordBreak: 'break-word' }}>
                        {tx.raw_description}
                      </div>
                      {tx.cleaned_merchant && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 3 }}>
                          <span style={{
                            fontSize: '0.68rem',
                            fontWeight: 600,
                            color: 'var(--text-muted)',
                            background: 'rgba(255, 255, 255, 0.04)',
                            padding: '1px 6px',
                            borderRadius: 4,
                            border: '1px solid var(--border-subtle)',
                          }}>
                            Clean: {tx.cleaned_merchant}
                          </span>
                          {tx.user_overridden && (
                            <span style={{ fontSize: '0.68rem', color: '#818cf8', fontWeight: 600 }}>
                              (User rule)
                            </span>
                          )}
                        </div>
                      )}
                    </td>

                    {/* Amount */}
                    <td style={{ padding: '12px 14px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                      <span
                        className="mono-text"
                        style={{
                          fontWeight: 700,
                          fontSize: '0.9rem',
                          color: isRefund
                            ? '#38bdf8'
                            : isPositive
                            ? '#34d399'
                            : '#f8fafc',
                        }}
                      >
                        {formatCurrency(tx.amount)}
                      </span>
                      {tx.deductible_amount > 0 && tx.deductibility_pct < 1.0 && (
                        <div style={{ fontSize: '0.68rem', color: '#fbbf24', fontWeight: 600 }}>
                          Deductible: {formatCurrency(tx.deductible_amount)} (50%)
                        </div>
                      )}
                    </td>

                    {/* Category */}
                    <td style={{ padding: '12px 14px' }}>
                      <span
                        className="badge"
                        style={{
                          background: `${tx.color}22`,
                          color: tx.color || '#fff',
                          border: `1px solid ${tx.color}55`,
                        }}
                      >
                        {isNeedsReview && <AlertTriangle size={12} />}
                        <span>{tx.category}</span>
                      </span>
                    </td>

                    {/* Confidence Meter */}
                    <td style={{ padding: '12px 14px', whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{
                          width: 48,
                          height: 5,
                          borderRadius: 3,
                          background: 'rgba(255, 255, 255, 0.08)',
                          overflow: 'hidden',
                        }}>
                          <div style={{
                            width: `${Math.round(tx.confidence * 100)}%`,
                            height: '100%',
                            background: tx.confidence >= 0.85 ? '#34d399' : tx.confidence >= 0.6 ? '#fbbf24' : '#ef4444',
                          }} />
                        </div>
                        <span style={{
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          color: tx.confidence >= 0.85 ? '#34d399' : tx.confidence >= 0.6 ? '#fbbf24' : '#ef4444',
                        }}>
                          {Math.round(tx.confidence * 100)}%
                        </span>
                      </div>
                    </td>

                    {/* Schedule C Line */}
                    <td style={{ padding: '12px 14px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {tx.schedule_c_line}
                    </td>

                    {/* Brain's Reasoning */}
                    <td style={{ padding: '12px 14px', fontSize: '0.78rem', color: 'var(--text-secondary)', maxWidth: 260 }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6 }}>
                        <HelpCircle size={14} color="var(--text-muted)" style={{ flexShrink: 0, marginTop: 2 }} />
                        <span>{tx.reason}</span>
                      </div>
                      {tx.suggested_category && (
                        <div style={{ marginTop: 4, fontSize: '0.72rem', color: '#fbbf24' }}>
                          Suggested: <strong>{tx.suggested_category}</strong>
                        </div>
                      )}
                    </td>

                    {/* Action Button */}
                    <td style={{ padding: '12px 14px', textAlign: 'center' }}>
                      <button
                        onClick={() => onReviewClick(tx)}
                        className={`btn btn-sm ${isNeedsReview ? 'btn-amber' : 'btn-secondary'}`}
                        style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                      >
                        <Edit2 size={12} />
                        <span>{isNeedsReview ? 'Review' : 'Fix'}</span>
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
