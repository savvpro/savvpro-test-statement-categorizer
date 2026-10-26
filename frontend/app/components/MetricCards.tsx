"use client";

import React from "react";
import {
  AlertExclamationIcon,
  ArrowRightIcon,
  DocumentIcon,
  MiniCheckIcon,
  ShoppingBagIcon,
  TrendArrowUpRightIcon,
  TrendingUpIcon,
} from "./Icons";
import { SummaryData } from "../types";

interface MetricCardsProps {
  summary: SummaryData | null;
  onReviewNow: () => void;
}

export function MetricCards({ summary, onReviewNow }: MetricCardsProps) {
  const totalExpDollars = summary
    ? `$${(Math.abs(summary.total_expense_cents) / 100).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })}`
    : "$0.00";

  const busExpDollars = summary
    ? `$${(Math.abs(summary.total_deductible_cents) / 100).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })}`
    : "$0.00";

  const incomeDollars = summary
    ? `$${(summary.total_income_cents / 100).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })}`
    : "$0.00";

  const needsReviewCount = summary?.status_counts?.needs_review ?? 0;
  const totalCount = summary?.status_counts?.total ?? 0;

  // outflow ratio calculation
  const outflowPct =
    summary && summary.total_expense_cents !== 0
      ? Math.min(
          100,
          Math.round(
            (Math.abs(summary.total_deductible_cents) /
              Math.max(1, Math.abs(summary.total_expense_cents))) *
              100
          )
        )
      : 0;


  return (
    <div className="metrics-grid">
      {/* 1. Total Expenses */}
      <div className="card metric-card">
        <div className="metric-card-top">
          <span className="metric-label">Total Expenses</span>
          <div className="metric-icon-box blue">
            <DocumentIcon size={18} />
          </div>
        </div>
        <div className="metric-value">{totalExpDollars}</div>
        <div className="metric-footer">
          <span>Recorded expenses</span>
          <span className="metric-pill gray">{totalCount} total</span>
        </div>
      </div>

      {/* 2. Business Expenses */}
      <div className="card metric-card">
        <div className="metric-card-top">
          <span className="metric-label">Business Expenses</span>
          <div className="metric-icon-box blue">
            <ShoppingBagIcon size={18} />
          </div>
        </div>
        <div className="metric-value">{busExpDollars}</div>
        <div className="metric-footer">
          <span>Currently categorized</span>
          <span className="metric-pill green" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <TrendArrowUpRightIcon size={12} />
            <span>{outflowPct}% outflow</span>
          </span>
        </div>
      </div>

      {/* 3. Income */}
      <div className="card metric-card">
        <div className="metric-card-top">
          <span className="metric-label">Income</span>
          <div className="metric-icon-box green">
            <TrendingUpIcon size={18} />
          </div>
        </div>
        <div className="metric-value green">{incomeDollars}</div>
        <div className="metric-footer">
          <span>Recorded incoming</span>
          <span className="metric-pill green" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <MiniCheckIcon size={12} />
            <span>100% categorized</span>
          </span>
        </div>
      </div>

      {/* 4. Needs Review */}
      <div className="card metric-card">
        <div className="metric-card-top">
          <div style={{ display: "flex", alignItems: "center" }}>
            <span className="metric-label">Needs Review</span>
            <span className="metric-label-dot" />
          </div>
          <div className="metric-icon-box amber">
            <AlertExclamationIcon size={18} />
          </div>
        </div>
        <div className="metric-value">{needsReviewCount}</div>
        <div className="metric-footer">
          <span>Action required</span>
          <button className="review-link" onClick={onReviewNow}>
            <span>Review Now</span>
            <ArrowRightIcon size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
