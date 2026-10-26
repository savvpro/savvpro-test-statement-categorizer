"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell } from "../components/AppShell";
import { AssignModal } from "../components/AssignModal";
import { fetchStatements, fetchTransactions } from "../api";
import { StatementItem, Transaction, ModalTransaction } from "../types";
import { ChevronDownIcon, EditPencilIcon, StoreIcon } from "../components/Icons";

function TransactionsContent() {
  const searchParams = useSearchParams();
  const queryStatus = searchParams.get("status") || "";

  const [statements, setStatements] = useState<StatementItem[]>([]);
  const [activeStatementId, setActiveStatementId] = useState<number | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>(queryStatus);
  const [search, setSearch] = useState<string>("");
  const [selectedTx, setSelectedTx] = useState<ModalTransaction | null>(null);
  const [assignOpen, setAssignOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (queryStatus) {
      setStatusFilter(queryStatus);
    }
  }, [queryStatus]);

  const loadData = async (statementId?: number, currentStatus?: string) => {
    setLoading(true);
    try {
      let stmts = statements;
      if (stmts.length === 0) {
        stmts = await fetchStatements();
        setStatements(stmts);
      }
      const sId = statementId || activeStatementId || (stmts.length > 0 ? stmts[0].id : null);
      if (sId) {
        setActiveStatementId(sId);
        const filterToUse = currentStatus !== undefined ? currentStatus : statusFilter;
        const res = await fetchTransactions(sId, {
          status: filterToUse || undefined,
          search: search || undefined,
          limit: 100,
        });
        if (res) {
          setTransactions(res.items);
          setTotalCount(res.total);
        }
      } else {
        setTransactions([]);
        setTotalCount(0);
      }
    } catch (err) {
      console.error("Error loading transactions:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(activeStatementId ?? undefined, statusFilter);
  }, [statusFilter, activeStatementId]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadData();
  };

  return (
    <AppShell
      pageTitle="Transactions Activity"
      pageSubtitle="Review all imported statement lines, assign Schedule C categories, and resolve unassigned rows."
      onStatementUploaded={() => loadData()}
    >
      <div className="card" style={{ padding: "20px 24px" }}>
        {/* Controls */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 20,
            gap: 16,
            flexWrap: "wrap",
          }}
        >
          {/* Search bar */}
          <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: 8, flex: 1, maxWidth: 420 }}>
            <input
              type="text"
              placeholder="Search merchant, description or amount..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="form-input"
            />
            <button type="submit" className="outline-btn" style={{ padding: "8px 16px" }}>
              Search
            </button>
          </form>

          {/* Statement selector if multiple statements */}
          {statements.length > 1 && (
            <select
              className="form-select"
              style={{ width: "auto" }}
              value={activeStatementId || ""}
              onChange={(e) => {
                const id = Number(e.target.value);
                setActiveStatementId(id);
                loadData(id);
              }}
            >
              {statements.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.filename} ({s.account_type})
                </option>
              ))}
            </select>
          )}

          {/* Status filter tabs */}
          <div className="toggle-group">
            <button
              className={`toggle-btn ${statusFilter === "" ? "active" : ""}`}
              onClick={() => setStatusFilter("")}
            >
              All
            </button>
            <button
              className={`toggle-btn ${statusFilter === "needs_review" ? "active" : ""}`}
              onClick={() => setStatusFilter("needs_review")}
            >
              Needs Review
            </button>
            <button
              className={`toggle-btn ${statusFilter === "auto" ? "active" : ""}`}
              onClick={() => setStatusFilter("auto")}
            >
              Auto
            </button>
            <button
              className={`toggle-btn ${statusFilter === "user_confirmed" ? "active" : ""}`}
              onClick={() => setStatusFilter("user_confirmed")}
            >
              Confirmed
            </button>
          </div>
        </div>

        {/* Data Table */}
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Description</th>
                <th>Category</th>
                <th>Confidence</th>
                <th>Amount</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", padding: "32px", color: "#64748b" }}>
                    Loading transactions...
                  </td>
                </tr>
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
                    <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>No transactions found</div>
                    <div style={{ fontSize: 12 }}>
                      {statements.length === 0
                        ? "Upload a bank or credit card statement to view transactions."
                        : "No transactions match your current search or status filter."}
                    </div>
                  </td>
                </tr>
              ) : (
                transactions.map((tx) => (
                  <tr key={tx.id}>
                    <td className="tx-date">{tx.posted_date}</td>
                    <td style={{ fontWeight: 600, color: "#0f172a" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <div className="tx-merchant-icon">
                          <StoreIcon size={16} />
                        </div>
                        <div>
                          <div>{tx.raw_description}</div>
                          {tx.reason && (
                            <div style={{ fontSize: 11, color: "#64748b", fontWeight: 400 }}>
                              {tx.reason}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>
                      <span
                        className={
                          tx.status === "needs_review"
                            ? "tx-category needs-review"
                            : "tx-category"
                        }
                      >
                        {tx.category.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td style={{ fontSize: 12, color: "#64748b" }}>
                      {tx.confidence > 0 ? `${Math.round(tx.confidence * 100)}%` : "Manual"}
                    </td>
                    <td>
                      <span
                        className={`tx-amount ${
                          tx.amount_cents > 0 ? "positive" : "negative"
                        }`}
                      >
                        {tx.amount_dollars}
                      </span>
                    </td>
                    <td>
                      <span className={`status-pill ${tx.status}`}>
                        {tx.status === "needs_review"
                          ? "Needs Review"
                          : tx.status === "auto"
                          ? "Auto Categorized"
                          : tx.status === "user_confirmed"
                          ? "User Confirmed"
                          : "Suggested"}
                      </span>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      {tx.status === "needs_review" ? (
                        <button
                          className="assign-btn"
                          onClick={() => {
                            setSelectedTx({
                              id: tx.id,
                              description: tx.raw_description,
                              category: tx.category,
                              amount: tx.amount_dollars,
                              isPositive: tx.amount_cents > 0,
                              date: tx.posted_date,
                              rawTx: tx,
                            });
                            setAssignOpen(true);
                          }}
                        >
                          <span>Assign</span>
                          <ChevronDownIcon size={12} />
                        </button>
                      ) : (
                        <button
                          className="action-icon-btn"
                          onClick={() => {
                            setSelectedTx({
                              id: tx.id,
                              description: tx.raw_description,
                              category: tx.category,
                              amount: tx.amount_dollars,
                              isPositive: tx.amount_cents > 0,
                              date: tx.posted_date,
                              rawTx: tx,
                            });
                            setAssignOpen(true);
                          }}
                          aria-label="Edit category"
                        >
                          <EditPencilIcon size={16} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <AssignModal
        isOpen={assignOpen}
        transaction={selectedTx}
        statementId={activeStatementId ?? 1}
        onClose={() => setAssignOpen(false)}
        onUpdated={() => loadData()}
      />
    </AppShell>
  );
}

export default function TransactionsPage() {
  return (
    <Suspense fallback={<div style={{ padding: 40, textAlign: "center", color: "#64748b" }}>Loading transactions...</div>}>
      <TransactionsContent />
    </Suspense>
  );
}

