import React from 'react';
import { SummaryResponse } from '../types';
import { TrendingDown, TrendingUp, HelpCircle, ArrowRightLeft, DollarSign, RotateCcw } from 'lucide-react';

interface SummaryCardsProps {
  summary: SummaryResponse;
  onFilterNeedsReview: () => void;
  isNeedsReviewActive: boolean;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({
  summary,
  onFilterNeedsReview,
  isNeedsReviewActive,
}) => {
  const formatMoney = (val: string | number) => {
    const num = parseFloat(String(val));
    if (isNaN(num)) return '$0.00';
    return `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const netNum = parseFloat(summary.net_operating_total);
  const isNetPositive = netNum >= 0;

  return (
    <div className="summary-grid">
      {/* Total Expenses */}
      <div className="summary-card">
        <div className="summary-card-header">
          <span className="summary-card-title">Operating Expenses</span>
          <TrendingDown size={18} color="#f87171" />
        </div>
        <div className="summary-card-value" style={{ color: '#f87171' }}>
          {formatMoney(summary.total_expenses)}
        </div>
        <div className="summary-card-subtext">
          Sum of deductible Schedule C business categories
        </div>
      </div>

      {/* Total Gross Income */}
      <div className="summary-card">
        <div className="summary-card-header">
          <span className="summary-card-title">Client Revenue</span>
          <TrendingUp size={18} color="#34d399" />
        </div>
        <div className="summary-card-value" style={{ color: '#34d399' }}>
          {formatMoney(summary.total_income)}
        </div>
        <div className="summary-card-subtext">
          Inbound client payments and paid project invoices
        </div>
      </div>

      {/* Net Operating Total */}
      <div className="summary-card">
        <div className="summary-card-header">
          <span className="summary-card-title">Net Operating Cash Flow</span>
          <DollarSign size={18} color={isNetPositive ? '#34d399' : '#f87171'} />
        </div>
        <div className="summary-card-value" style={{ color: isNetPositive ? '#34d399' : '#f87171' }}>
          {formatMoney(summary.net_operating_total)}
        </div>
        <div className="summary-card-subtext">
          Revenue - Deductible Expenses + Recovered Refunds
        </div>
      </div>

      {/* Needs Review Alert Card */}
      <div
        className={`summary-card alert-card ${isNeedsReviewActive ? 'active' : ''}`}
        style={{ cursor: summary.total_needs_review_count > 0 ? 'pointer' : 'default' }}
        onClick={() => {
          if (summary.total_needs_review_count > 0) {
            onFilterNeedsReview();
          }
        }}
        title="Click to view all transactions requiring verification"
      >
        <div className="summary-card-header">
          <span className="summary-card-title" style={{ color: 'var(--color-warning)' }}>
            Needs Review
          </span>
          <HelpCircle size={18} color="var(--color-warning)" />
        </div>
        <div className="summary-card-value" style={{ color: 'var(--color-warning)' }}>
          {summary.total_needs_review_count} <span style={{ fontSize: '1rem', fontWeight: 500 }}>({formatMoney(summary.total_needs_review_amount)})</span>
        </div>
        <div className="summary-card-subtext" style={{ color: '#fbbf24' }}>
          {summary.total_needs_review_count > 0
            ? '⚠️ Click to filter and resolve uncertain rows'
            : '✓ All transactions verified'}
        </div>
      </div>

      {/* Non-Operating (Refunds & Transfers) */}
      <div className="summary-card">
        <div className="summary-card-header">
          <span className="summary-card-title">Transfers & Refunds</span>
          <ArrowRightLeft size={18} color="#94a3b8" />
        </div>
        <div className="summary-card-value" style={{ fontSize: '1.25rem', marginTop: '4px' }}>
          <div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Transfers: </span>
            <span>{formatMoney(summary.total_transfers)}</span>
          </div>
          <div style={{ marginTop: '4px' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Refunds: </span>
            <span style={{ color: '#38bdf8' }}>{formatMoney(summary.total_refunds)}</span>
          </div>
        </div>
        <div className="summary-card-subtext">
          Transfers excluded from spend; Refunds offset expenses
        </div>
      </div>
    </div>
  );
};
