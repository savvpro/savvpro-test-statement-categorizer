"use client";

import React from "react";
import {
  ArrowRightIcon,
  CarIcon,
  CashPaymentIcon,
  ChevronDownIcon,
  EditPencilIcon,
  EyeViewIcon,
  QuestionMarkIcon,
  StoreIcon,
  UtensilsIcon,
} from "./Icons";
import { ModalTransaction, Transaction } from "../types";

interface RecentTransactionsProps {
  transactions?: Transaction[];
  totalCount?: number;
  onViewAll: () => void;
  onAssignTransaction: (tx: ModalTransaction) => void;
}

export function RecentTransactions({
  transactions,
  totalCount = 0,
  onViewAll,
  onAssignTransaction,
}: RecentTransactionsProps) {
  // Helper to pick merchant icon
  const getIcon = (category: string, desc: string) => {
    const c = category.toLowerCase();
    const d = desc.toLowerCase();
    if (c.includes("meal") || d.includes("restaurant") || d.includes("cafe")) return <UtensilsIcon size={16} />;
    if (c.includes("income") || d.includes("payment") || d.includes("payout") || d.includes("client")) return <CashPaymentIcon size={16} />;
    if (c.includes("office") || d.includes("staples") || d.includes("store")) return <StoreIcon size={16} />;
    if (c.includes("travel") || d.includes("uber") || d.includes("airline") || d.includes("transit")) return <CarIcon size={16} />;
    if (c.includes("needs_review") || c.includes("review")) return <QuestionMarkIcon size={16} />;
    return <StoreIcon size={16} />;
  };

  const rows =
    transactions && transactions.length > 0
      ? transactions.slice(0, 5).map((t) => ({
          id: t.id,
          date: t.posted_date,
          description: t.raw_description,
          category: t.category.replace(/_/g, " "),
          amount: t.amount_dollars,
          isPositive: t.amount_cents > 0,
          status: t.status,
          icon: getIcon(t.category, t.raw_description),
          isNeedsReview: t.status === "needs_review",
          isViewAction: t.amount_cents > 0,
          rawTx: t,
        }))
      : [];


  return (
    <div className="card transactions-card">
      {/* Header */}
      <div className="tx-card-header">
        <div>
          <div className="card-title">Recent transactions</div>
          <div className="page-subtitle" style={{ fontSize: 13, marginTop: 2 }}>
            Latest imported bank activity
          </div>
        </div>

        <button className="tx-view-all-link" onClick={onViewAll}>
          <span>View all ({totalCount})</span>
          <ArrowRightIcon size={14} />
        </button>
      </div>

      {/* Table */}
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Description</th>
              <th>Category</th>
              <th>Amount</th>
              <th>Status</th>
              <th style={{ textAlign: "right" }}>Quick Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", padding: "36px 20px", color: "#64748b" }}>
                  <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 4 }}>No transactions recorded yet</div>
                  <div style={{ fontSize: 12 }}>Upload a bank or credit card statement to automatically categorize your transactions.</div>
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id}>
                <td className="tx-date">{row.date}</td>

                <td>
                  <div className="tx-desc-cell">
                    <div className="tx-merchant-icon">{row.icon}</div>
                    <span className="tx-merchant-name">{row.description}</span>
                  </div>
                </td>

                <td>
                  <span
                    className={`tx-category ${
                      row.isNeedsReview ? "needs-review" : ""
                    }`}
                  >
                    {row.isNeedsReview ? "Needs Review" : row.category}
                  </span>
                </td>

                <td>
                  <span
                    className={`tx-amount ${
                      row.isPositive ? "positive" : "negative"
                    }`}
                  >
                    {row.amount}
                  </span>
                </td>

                <td>
                  <span
                    className={`status-pill ${
                      row.isNeedsReview ? "needs_review" : "categorized"
                    }`}
                  >
                    {row.isNeedsReview ? "Needs Review" : "Categorized"}
                  </span>
                </td>

                <td>
                  <div className="quick-action-cell">
                    {row.isNeedsReview ? (
                      <button
                        className="assign-btn"
                        onClick={() => onAssignTransaction(row)}
                      >
                        <span>Assign</span>
                        <ChevronDownIcon size={12} />
                      </button>
                    ) : row.isViewAction ? (
                      <button
                        className="action-icon-btn"
                        aria-label="View transaction"
                        onClick={() => onAssignTransaction(row)}
                      >
                        <EyeViewIcon size={16} />
                      </button>
                    ) : (
                      <button
                        className="action-icon-btn"
                        aria-label="Edit transaction"
                        onClick={() => onAssignTransaction(row)}
                      >
                        <EditPencilIcon size={16} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
