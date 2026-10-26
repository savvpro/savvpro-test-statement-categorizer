import React from 'react';
import { DollarSign, TrendingDown, AlertTriangle, ArrowRightLeft, Percent, CheckCircle2 } from 'lucide-react';

export default function MetricsOverview({ taxSummary, onFilterNeedsReview, isNeedsReviewActive }) {
  if (!taxSummary) return null;

  const formatCurrency = (amt) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amt || 0);
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
      {/* Gross Income Card */}
      <div className="glass-panel" style={{ padding: '20px 24px', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute',
          top: -20,
          right: -20,
          width: 90,
          height: 90,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(16, 185, 129, 0.2) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Gross Business Income
          </span>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: 'rgba(16, 185, 129, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <DollarSign size={18} color="#34d399" />
          </div>
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#34d399', letterSpacing: '-0.02em' }}>
          {formatCurrency(taxSummary.gross_income)}
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
          IRS Line 1: Client Invoices & Payouts
        </div>
      </div>

      {/* Deductible Expenses Card */}
      <div className="glass-panel" style={{ padding: '20px 24px', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute',
          top: -20,
          right: -20,
          width: 90,
          height: 90,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(99, 102, 241, 0.2) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Deductible Expenses
          </span>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: 'rgba(99, 102, 241, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <TrendingDown size={18} color="#818cf8" />
          </div>
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#a5b4fc', letterSpacing: '-0.02em' }}>
          {formatCurrency(taxSummary.total_deductible_expenses)}
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4, display: 'flex', gap: 6, alignItems: 'center' }}>
          <span>Raw: {formatCurrency(taxSummary.total_raw_expenses)}</span>
          <span>•</span>
          <span style={{ color: '#fbbf24', fontWeight: 600 }}>Includes 50% Meals Limit</span>
        </div>
      </div>

      {/* Net Taxable Profit Card */}
      <div className="glass-panel" style={{ padding: '20px 24px', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute',
          top: -20,
          right: -20,
          width: 90,
          height: 90,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(59, 130, 246, 0.2) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Net Taxable Profit
          </span>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: 'rgba(59, 130, 246, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Percent size={18} color="#60a5fa" />
          </div>
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#60a5fa', letterSpacing: '-0.02em' }}>
          {formatCurrency(taxSummary.net_taxable_profit)}
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
          Schedule C Net Profit (Line 31)
        </div>
      </div>

      {/* Needs Review Card */}
      <div className="glass-panel" style={{
        padding: '20px 24px',
        position: 'relative',
        overflow: 'hidden',
        border: taxSummary.needs_review_count > 0 ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid var(--border-subtle)',
        background: taxSummary.needs_review_count > 0 ? 'rgba(245, 158, 11, 0.05)' : 'var(--bg-card)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Needs Review
          </span>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: taxSummary.needs_review_count > 0 ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            {taxSummary.needs_review_count > 0 ? (
              <AlertTriangle size={18} color="#f59e0b" />
            ) : (
              <CheckCircle2 size={18} color="#34d399" />
            )}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
          <div style={{
            fontSize: '1.75rem',
            fontWeight: 800,
            color: taxSummary.needs_review_count > 0 ? '#fbbf24' : '#34d399',
            letterSpacing: '-0.02em'
          }}>
            {taxSummary.needs_review_count} {taxSummary.needs_review_count === 1 ? 'Row' : 'Rows'}
          </div>
          {taxSummary.needs_review_count > 0 && (
            <button
              onClick={onFilterNeedsReview}
              className={`btn btn-sm ${isNeedsReviewActive ? 'btn-primary' : 'btn-amber'}`}
              style={{ fontSize: '0.75rem' }}
            >
              {isNeedsReviewActive ? 'Showing All' : 'Review Rows'}
            </button>
          )}
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
          {taxSummary.needs_review_count > 0
            ? `${formatCurrency(taxSummary.review_required_amount)} pending human verification`
            : 'All rows verified and classified!'}
        </div>
      </div>
    </div>
  );
}
