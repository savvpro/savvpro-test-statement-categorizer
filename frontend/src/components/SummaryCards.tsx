import React from "react";
import type { StatementSummary } from "../types";
import {
  TrendingUp,
  Receipt,
  ArrowLeftRight,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";

interface SummaryCardsProps {
  summary: StatementSummary;
  onFilterNeedsReview: () => void;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({
  summary,
  onFilterNeedsReview,
}) => {
  return (
    <div className="summary-grid">
      {/* Gross Income Card */}
      <div className="summary-card income-card">
        <div className="card-header">
          <span className="card-label">Gross Revenue / Income</span>
          <div className="card-icon-wrap income-icon">
            <TrendingUp size={18} />
          </div>
        </div>
        <div className="card-value">${summary.total_income.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
        <div className="card-footnote">Client payouts & deposits</div>
      </div>

      {/* Net Deductible Expenses Card */}
      <div className="summary-card expense-card">
        <div className="card-header">
          <span className="card-label">Net Tax-Deductible Expenses</span>
          <div className="card-icon-wrap expense-icon">
            <Receipt size={18} />
          </div>
        </div>
        <div className="card-value">${summary.total_expenses.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
        <div className="card-footnote">Adjusted for refunds & offsets</div>
      </div>

      {/* Internal Transfers Card */}
      <div className="summary-card transfer-card">
        <div className="card-header">
          <span className="card-label">Non-Spending Transfers</span>
          <div className="card-icon-wrap transfer-icon">
            <ArrowLeftRight size={18} />
          </div>
        </div>
        <div className="card-value">${summary.total_transfers.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
        <div className="card-footnote">Savings, card autopay & internal</div>
      </div>

      {/* Expense Refunds Card */}
      <div className="summary-card refund-card">
        <div className="card-header">
          <span className="card-label">Expense Refunds & Offsets</span>
          <div className="card-icon-wrap refund-icon">
            <RotateCcw size={18} />
          </div>
        </div>
        <div className="card-value">${summary.total_refunds.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
        <div className="card-footnote">Money back (never counted as income)</div>
      </div>

      {/* Needs Review & Review Progress Card */}
      <div
        className={`summary-card review-card ${
          summary.needs_review_count > 0 ? "needs-attention" : "all-reviewed"
        }`}
        onClick={onFilterNeedsReview}
        style={{ cursor: summary.needs_review_count > 0 ? "pointer" : "default" }}
      >
        <div className="card-header">
          <span className="card-label">Review Status</span>
          <div
            className={`card-icon-wrap ${
              summary.needs_review_count > 0 ? "review-icon" : "complete-icon"
            }`}
          >
            {summary.needs_review_count > 0 ? (
              <AlertTriangle size={18} />
            ) : (
              <CheckCircle2 size={18} />
            )}
          </div>
        </div>
        <div className="card-value">
          {summary.needs_review_count > 0
            ? `${summary.needs_review_count} Rows Need Review`
            : "All Verified"}
        </div>
        <div className="progress-container">
          <div className="progress-bar-bg">
            <div
              className="progress-bar-fill"
              style={{ width: `${summary.review_progress_percent}%` }}
            />
          </div>
          <span className="progress-text">
            {summary.review_progress_percent}% tax ready
          </span>
        </div>
      </div>
    </div>
  );
};
