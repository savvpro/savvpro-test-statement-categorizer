"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "./components/AppShell";
import { MetricCards } from "./components/MetricCards";
import { ExpensesByCategory } from "./components/ExpensesByCategory";
import { TaxReadiness } from "./components/TaxReadiness";
import { RecentTransactions } from "./components/RecentTransactions";
import { AssignModal } from "./components/AssignModal";
import { fetchStatements, fetchSummary, fetchTransactions } from "./api";
import { ModalTransaction, StatementItem, SummaryData, Transaction } from "./types";
import { FilterSlidersIcon } from "./components/Icons";

export default function DashboardPage() {
  const router = useRouter();
  const [statements, setStatements] = useState<StatementItem[]>([]);
  const [activeStatementId, setActiveStatementId] = useState<number | null>(null);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [txTotalCount, setTxTotalCount] = useState<number>(0);
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [selectedTx, setSelectedTx] = useState<ModalTransaction | null>(null);

  const loadData = useCallback(async () => {
    try {
      const stmts = await fetchStatements();
      setStatements(stmts);
      if (stmts && stmts.length > 0) {
        const id = stmts[0].id;
        setActiveStatementId(id);
        const sum = await fetchSummary(id);
        if (sum) setSummary(sum);

        const txRes = await fetchTransactions(id, { limit: 10 });
        if (txRes) {
          setTransactions(txRes.items);
          setTxTotalCount(txRes.total);
        }
      } else {
        setActiveStatementId(null);
        setSummary(null);
        setTransactions([]);
        setTxTotalCount(0);
      }
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const fetchDashboard = async () => {
      try {
        const stmts = await fetchStatements();
        if (!active) return;
        setStatements(stmts);
        if (stmts && stmts.length > 0) {
          const id = stmts[0].id;
          setActiveStatementId(id);
          const sum = await fetchSummary(id);
          if (!active) return;
          if (sum) setSummary(sum);

          const txRes = await fetchTransactions(id, { limit: 10 });
          if (!active) return;
          if (txRes) {
            setTransactions(txRes.items);
            setTxTotalCount(txRes.total);
          }
        }
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      }
    };

    fetchDashboard();

    return () => {
      active = false;
    };
  }, []);

  const handleTransactionUpdated = async () => {
    if (activeStatementId) {
      const sum = await fetchSummary(activeStatementId);
      if (sum) setSummary(sum);
      const txRes = await fetchTransactions(activeStatementId, { limit: 10 });
      if (txRes) {
        setTransactions(txRes.items);
        setTxTotalCount(txRes.total);
      }
    }
  };

  return (
    <AppShell onStatementUploaded={loadData}>
      {/* Header Banner */}
      <div className="header-banner">
        <div>
          <h1 className="page-title">Your financial overview</h1>
          <p className="page-subtitle">
            Review your transactions and prepare your records for tax time.
          </p>
        </div>

        <div className="header-actions">
          {statements.length > 1 && (
            <select
              className="outline-btn"
              value={activeStatementId || ""}
              onChange={async (e) => {
                const id = Number(e.target.value);
                setActiveStatementId(id);
                const sum = await fetchSummary(id);
                if (sum) setSummary(sum);
                const txRes = await fetchTransactions(id, { limit: 10 });
                if (txRes) {
                  setTransactions(txRes.items);
                  setTxTotalCount(txRes.total);
                }
              }}
            >
              {statements.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.filename} ({s.account_type})
                </option>
              ))}
            </select>
          )}

          <button
            className="outline-btn"
            onClick={() => alert("Tax Year 2026 active (Jan 1 – Dec 31, 2026)")}
          >
            <FilterSlidersIcon size={14} />
            <span>Filter Tax Year</span>
          </button>
        </div>
      </div>

      {/* Top 4 KPI Metric Cards */}
      <MetricCards
        summary={summary}
        onReviewNow={() => router.push("/transactions?status=needs_review")}
      />

      {/* Middle Grid (Expenses By Category + Tax Readiness) */}
      <div className="middle-grid">
        <ExpensesByCategory totals={summary?.totals} />
        <TaxReadiness
          summary={summary}
          onResolveUnassigned={() => router.push("/transactions?status=needs_review")}
        />
      </div>

      {/* Bottom Table: Recent Transactions */}
      <RecentTransactions
        transactions={transactions}
        totalCount={txTotalCount}
        onViewAll={() => router.push("/transactions")}
        onAssignTransaction={(tx) => {
          setSelectedTx(tx);
          setAssignModalOpen(true);
        }}
      />

      {/* Assign Modal */}
      <AssignModal
        isOpen={assignModalOpen}
        transaction={selectedTx}
        statementId={activeStatementId ?? 1}
        onClose={() => setAssignModalOpen(false)}
        onUpdated={handleTransactionUpdated}
      />
    </AppShell>
  );
}
