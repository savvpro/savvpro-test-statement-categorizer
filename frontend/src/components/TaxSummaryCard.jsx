import React, { useState } from 'react';
import { FileSpreadsheet, ChevronDown, ChevronUp, Info, HelpCircle } from 'lucide-react';

export default function TaxSummaryCard({ taxSummary }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!taxSummary || !taxSummary.categories) return null;

  const formatCurrency = (amt) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amt || 0);
  };

  const totalDeductible = taxSummary.total_deductible_expenses || 1;

  return (
    <div className="glass-panel" style={{ padding: '20px 24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: 'rgba(99, 102, 241, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <FileSpreadsheet size={18} color="#818cf8" />
          </div>
          <div>
            <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              IRS Schedule C Expense Breakdown
            </h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Calculated deductions ready for Form 1040 Schedule C filing
            </p>
          </div>
        </div>

        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="btn btn-secondary btn-sm"
          style={{ fontSize: '0.75rem' }}
        >
          {isExpanded ? (
            <>
              <span>Collapse</span>
              <ChevronUp size={14} />
            </>
          ) : (
            <>
              <span>View All Categories</span>
              <ChevronDown size={14} />
            </>
          )}
        </button>
      </div>

      {/* Category Progress Bars */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {taxSummary.categories
          .slice(0, isExpanded ? taxSummary.categories.length : 4)
          .map((cat, idx) => {
            const pctOfTotal = Math.min(100, Math.round((cat.deductible_amount / totalDeductible) * 100)) || 0;
            return (
              <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: cat.color || 'var(--accent-indigo)',
                      display: 'inline-block',
                    }} />
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {cat.category}
                    </span>
                    <span style={{
                      fontSize: '0.7rem',
                      color: 'var(--text-muted)',
                      padding: '1px 6px',
                      borderRadius: 4,
                      background: 'rgba(255, 255, 255, 0.04)',
                      border: '1px solid var(--border-subtle)',
                    }}>
                      {cat.schedule_c_line}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                    <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                      {formatCurrency(cat.deductible_amount)}
                    </span>
                    {cat.deductibility_pct < 1.0 && cat.deductibility_pct > 0 && (
                      <span style={{ fontSize: '0.7rem', color: '#fbbf24', fontWeight: 600 }}>
                        ({cat.deductibility_pct * 100}% Limit)
                      </span>
                    )}
                  </div>
                </div>

                {/* Progress bar */}
                <div style={{
                  width: '100%',
                  height: 6,
                  borderRadius: 3,
                  background: 'rgba(255, 255, 255, 0.06)',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    width: `${pctOfTotal}%`,
                    height: '100%',
                    borderRadius: 3,
                    background: cat.color || 'var(--accent-indigo)',
                    transition: 'width 0.4s ease',
                  }} />
                </div>
              </div>
            );
          })}
      </div>

      {/* Tax Law Notes Footer */}
      <div style={{
        marginTop: 16,
        paddingTop: 12,
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '0.75rem',
        color: 'var(--text-muted)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Info size={14} color="#818cf8" />
          <span>
            Non-deductible Transfers & Draws: {formatCurrency(taxSummary.total_non_expense_transfers)} (excluded)
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span>
            Refunds & Return Credits: {formatCurrency(taxSummary.total_refunds_offset)} (offset against expenses)
          </span>
        </div>
      </div>
    </div>
  );
}
