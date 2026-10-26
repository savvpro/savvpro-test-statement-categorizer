"use client";

import React, { useState } from "react";
import { ShieldCheckIcon } from "./Icons";
import { CategoryTotal } from "../types";

interface ExpensesByCategoryProps {
  totals?: CategoryTotal[];
}

export function ExpensesByCategory({ totals }: ExpensesByCategoryProps) {
  const [viewMode, setViewMode] = useState<"total" | "share">("total");

  // Map real backend totals
  const displayItems =
    totals && totals.length > 0
      ? (() => {
          const expenseRows = totals.filter(
            (t) => t.cat_type === "expense" || t.cat_type === "review"
          );
          const totalSum = expenseRows.reduce(
            (acc, curr) => acc + Math.abs(curr.total_cents),
            0
          );

          return expenseRows.map((t) => {
            const absCents = Math.abs(t.total_cents);
            const pct = totalSum > 0 ? (absCents / totalSum) * 100 : 0;
            return {
              name: t.label || t.category,
              sharePct: `${pct.toFixed(1)}%`,
              amount: `$${(absCents / 100).toLocaleString("en-US", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}`,
              pctVal: Math.max(2, pct),
              isAmber: t.category === "needs_review" || t.cat_type === "review",
              badge: t.deductible_pct === 50 ? "50% Rule Applies" : null,
            };
          });
        })()
      : [];


  return (
    <div className="card">
      {/* Card Header */}
      <div className="category-card-header">
        <div className="category-title-wrap">
          <span className="card-title">Expenses by category</span>
          <span className="schedule-c-badge">Schedule C Preview</span>
        </div>

        <div className="toggle-group">
          <button
            className={`toggle-btn ${viewMode === "total" ? "active" : ""}`}
            onClick={() => setViewMode("total")}
          >
            Total $
          </button>
          <button
            className={`toggle-btn ${viewMode === "share" ? "active" : ""}`}
            onClick={() => setViewMode("share")}
          >
            Share %
          </button>
        </div>
      </div>

      <div className="date-subtext">Jan 1 – Dec 31, 2026</div>

      {/* Categories Progress Breakdown */}
      <div className="category-list">
        {displayItems.length === 0 ? (
          <div
            style={{
              padding: "24px 16px",
              textAlign: "center",
              color: "#64748b",
              fontSize: 13,
              background: "#f8fafc",
              borderRadius: 8,
              border: "1px dashed #cbd5e1",
            }}
          >
            No expenses recorded yet. Upload a statement to view the Schedule C breakdown.
          </div>
        ) : (
          displayItems.map((item, idx) => (
            <div key={idx} className="category-row">
              <div className="category-row-meta">
                <div className="cat-label-wrap">
                  <span className={`cat-dot ${item.isAmber ? "amber" : ""}`} />
                  <span className="cat-name">{item.name}</span>
                  {item.badge && <span className="rule-pill">{item.badge}</span>}
                </div>

                <div className="cat-figures">
                  <span className="cat-pct">{item.sharePct}</span>
                  <span className="cat-amount">{item.amount}</span>
                </div>
              </div>

              <div className="progress-track">
                <div
                  className={`progress-fill ${item.isAmber ? "amber" : ""}`}
                  style={{ width: `${Math.min(100, item.pctVal)}%` }}
                />
              </div>
            </div>
          ))
        )}
      </div>

      {/* Compliance Assistant Callout Banner */}
      <div className="compliance-box">
        <div className="compliance-icon">
          <ShieldCheckIcon size={20} />
        </div>
        <div className="compliance-content">
          <span className="compliance-title">IRS Schedule C Compliance Assistant</span>
          <p className="compliance-desc">
            TaxSort categorizes expenses according to IRS Schedule C guidelines. You
            can deduct 50% of allowable business meals and 100% of validated business
            software subscriptions.
          </p>
        </div>
      </div>
    </div>
  );
}
