"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  CategorizedTransaction,
  FinancialSummary,
  TransactionType,
  BusinessCategory,
  BUSINESS_CATEGORIES,
  TRANSACTION_TYPES,
} from "../types";
import {
  parseStatementFile,
  loadDemoStatement,
  recalculateSummary,
  exportTransactionsToCSV,
  checkBackendHealth,
} from "../lib/api";

export default function StatementCategorizerPage() {
  const [transactions, setTransactions] = useState<CategorizedTransaction[]>([]);
  const [summary, setSummary] = useState<FinancialSummary | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  // Drag & drop state
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check backend health on mount
  useEffect(() => {
    checkBackendHealth().then((isHealthy) => setBackendOnline(isHealthy));
  }, []);

  const handleFileUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setErrorMessage("Please select a standard CSV file (.csv).");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setWarnings([]);

    try {
      const response = await parseStatementFile(file);
      setTransactions(response.transactions);
      setSummary(response.summary);
      setWarnings(response.warnings || []);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("An unexpected error occurred while parsing the statement.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadDemo = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    setWarnings([]);

    try {
      const response = await loadDemoStatement();
      setTransactions(response.transactions);
      setSummary(response.summary);
      setWarnings(response.warnings || []);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Unable to connect to the backend API. Please ensure the backend is running on port 8000.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateTransaction = async (
    id: number,
    field: "business_category" | "transaction_type",
    value: string
  ) => {
    const updated = transactions.map((t) => {
      if (t.id !== id) return t;
      const updatedItem = {
        ...t,
        [field]: value,
        review_status: "user_corrected" as const,
        explanation: `Manually changed ${
          field === "business_category" ? "category" : "type"
        } to '${value}'.`,
      };
      return updatedItem;
    });

    setTransactions(updated);

    try {
      const newSummary = await recalculateSummary(updated);
      setSummary(newSummary);
    } catch (e) {
      console.error("Recalculate error:", e);
    }
  };

  const handleConfirmTransaction = async (id: number) => {
    const updated = transactions.map((t) => {
      if (t.id !== id) return t;
      return {
        ...t,
        review_status: "user_confirmed" as const,
        explanation: `${t.explanation} (Verified by user)`,
      };
    });

    setTransactions(updated);

    try {
      const newSummary = await recalculateSummary(updated);
      setSummary(newSummary);
    } catch (e) {
      console.error("Recalculate error:", e);
    }
  };

  const handleExportCSV = () => {
    if (transactions.length === 0) return;
    exportTransactionsToCSV(transactions, "reconciled_statement.csv");
  };

  const handleReset = () => {
    setTransactions([]);
    setSummary(null);
    setWarnings([]);
    setErrorMessage(null);
    setSearchQuery("");
    setStatusFilter("all");
    setCategoryFilter("all");
    setTypeFilter("all");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Filtered transactions
  const filteredTransactions = useMemo(() => {
    return transactions.filter((t) => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesDesc = t.description.toLowerCase().includes(q);
        const matchesAmt = t.amount.includes(q);
        const matchesRule = t.rule_id.toLowerCase().includes(q);
        if (!matchesDesc && !matchesAmt && !matchesRule) return false;
      }
      if (statusFilter !== "all" && t.review_status !== statusFilter) {
        return false;
      }
      if (categoryFilter !== "all" && t.business_category !== categoryFilter) {
        return false;
      }
      if (typeFilter !== "all" && t.transaction_type !== typeFilter) {
        return false;
      }
      return true;
    });
  }, [transactions, searchQuery, statusFilter, categoryFilter, typeFilter]);

  const formatCurrency = (val: string | number | undefined) => {
    if (val === undefined || val === null) return "$0.00";
    const num = typeof val === "string" ? parseFloat(val) : val;
    if (isNaN(num)) return "$0.00";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
    }).format(num);
  };

  // Status counts for filter chips
  const statusCounts = useMemo(() => {
    const counts = { all: transactions.length, needs_review: 0, auto: 0, user_confirmed: 0, user_corrected: 0 };
    for (const t of transactions) {
      if (t.review_status in counts) {
        counts[t.review_status as keyof typeof counts]++;
      }
    }
    return counts;
  }, [transactions]);

  const confirmedCount = statusCounts.auto + statusCounts.user_confirmed + statusCounts.user_corrected;
  const resolutionPercent = transactions.length > 0 ? Math.round((confirmedCount / transactions.length) * 100) : 100;

  return (
    <div className="min-h-screen flex flex-col bg-[#F8FAFC] text-slate-800 antialiased selection:bg-slate-200">
      {/* Top Application Bar */}
      <header className="bg-white border-b border-slate-200/80 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-slate-900 text-white flex items-center justify-center font-semibold text-sm shadow-sm tracking-tight">
              SC
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold text-slate-900 tracking-tight">
                  Statement Reconciler
                </h1>
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200/60">
                  Tax Year 2024
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                Business Transaction Ledger & Account Categorization
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {backendOnline !== null && (
              <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-md text-[11px] font-medium bg-slate-50 text-slate-600 border border-slate-200">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    backendOnline ? "bg-emerald-500" : "bg-rose-500"
                  }`}
                />
                {backendOnline ? "System Ready" : "Service Offline"}
              </div>
            )}

            {transactions.length > 0 && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleExportCSV}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium rounded-md shadow-sm transition"
                >
                  <svg className="w-3.5 h-3.5 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Export Reconciled CSV
                </button>
                <button
                  onClick={handleReset}
                  className="px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md border border-slate-200 transition"
                >
                  New Statement
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Error Alert */}
        {errorMessage && (
          <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 flex items-start gap-3">
            <svg className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1 text-xs font-medium">{errorMessage}</div>
            <button onClick={() => setErrorMessage(null)} className="text-rose-500 hover:text-rose-700 text-xs">
              ✕
            </button>
          </div>
        )}

        {/* Warnings Banner */}
        {warnings.length > 0 && (
          <div className="p-3.5 rounded-lg bg-amber-50/70 border border-amber-200/80 text-amber-900">
            <div className="flex items-center gap-2 font-medium text-xs mb-1 text-amber-900">
              <svg className="w-3.5 h-3.5 text-amber-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Statement Audit Notices ({warnings.length})
            </div>
            <ul className="list-disc list-inside text-[11px] space-y-0.5 text-amber-800 ml-1">
              {warnings.map((w, idx) => (
                <li key={idx}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Upload State (When no data is loaded) */}
        {transactions.length === 0 && (
          <div className="space-y-6 max-w-4xl mx-auto pt-4">
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  handleFileUpload(e.dataTransfer.files[0]);
                }
              }}
              className={`border border-dashed rounded-xl p-10 text-center transition ${
                isDragging
                  ? "border-slate-500 bg-slate-100/60"
                  : "border-slate-300 bg-white hover:border-slate-400 shadow-sm"
              }`}
            >
              <div className="max-w-md mx-auto space-y-4">
                <div className="w-12 h-12 mx-auto rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center border border-slate-200">
                  <svg className="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">
                    Upload Bank or Credit Card Statement
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Drag and drop your bank CSV file here, or browse from your computer.
                  </p>
                </div>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleFileUpload(e.target.files[0]);
                      }
                    }}
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isLoading}
                    className="w-full sm:w-auto px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium rounded-md shadow-sm transition disabled:opacity-50"
                  >
                    {isLoading ? "Analyzing Statement..." : "Select CSV File"}
                  </button>

                  <button
                    onClick={handleLoadDemo}
                    disabled={isLoading}
                    className="w-full sm:w-auto px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-medium rounded-md shadow-sm transition disabled:opacity-50"
                  >
                    Load Sample Statement
                  </button>
                </div>

                <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-400">
                  Expected schema: <span className="font-mono text-slate-600">Date, Description, Amount</span> (positive = money in, negative = money out).
                </div>
              </div>
            </div>

            {/* Standard Specifications Card */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm text-xs text-slate-600 space-y-3">
              <h4 className="font-semibold text-slate-900 text-xs uppercase tracking-wider">
                Statement Standard & Accounting Rules
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
                <div className="space-y-1">
                  <div className="font-medium text-slate-800">1. Transfer Isolation</div>
                  <p className="text-slate-500 text-[11px] leading-relaxed">
                    Internal transfers between savings and checking are strictly segregated from business operations and excluded from profit/loss.
                  </p>
                </div>
                <div className="space-y-1">
                  <div className="font-medium text-slate-800">2. Validated Refunds</div>
                  <p className="text-slate-500 text-[11px] leading-relaxed">
                    Vendor refunds offset corresponding operating expenses. Unmatched refunds are flagged for review rather than inflating revenue.
                  </p>
                </div>
                <div className="space-y-1">
                  <div className="font-medium text-slate-800">3. Deterministic Ledger</div>
                  <p className="text-slate-500 text-[11px] leading-relaxed">
                    Every transaction carries a verified rule ID and audit justification. Ambiguous items route to review for user confirmation.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Dashboard View (When statement data is populated) */}
        {transactions.length > 0 && summary && (
          <div className="space-y-5">
            {/* Reconciliation Progress Banner */}
            <div className="bg-white border border-slate-200 rounded-lg p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-md bg-slate-100 flex items-center justify-center font-bold text-slate-700 text-xs">
                  {resolutionPercent}%
                </div>
                <div>
                  <div className="font-medium text-slate-900">
                    Reconciliation Progress ({confirmedCount} of {transactions.length} items reviewed)
                  </div>
                  <div className="text-[11px] text-slate-500">
                    {summary.needs_review_count > 0
                      ? `${summary.needs_review_count} item${summary.needs_review_count > 1 ? "s" : ""} (${formatCurrency(summary.unclassified_amount)}) require manual verification before final filing.`
                      : "All transactions have been confirmed. Operating ledger is reconciled."}
                  </div>
                </div>
              </div>

              {summary.needs_review_count > 0 && (
                <button
                  onClick={() => setStatusFilter("needs_review")}
                  className="px-3 py-1.5 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300 rounded text-xs font-medium transition"
                >
                  View {summary.needs_review_count} Pending Items
                </button>
              )}
            </div>

            {/* Financial Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
              {/* Card 1: Gross Inflow (Income) */}
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    Operating Revenue
                  </span>
                  <span className="text-emerald-700 text-xs font-semibold">Inflow</span>
                </div>
                <div className="mt-2.5">
                  <div className="text-2xl font-semibold text-slate-900 tracking-tight">
                    {formatCurrency(summary.total_income)}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1">
                    Confirmed client invoices & receipts
                  </div>
                </div>
              </div>

              {/* Card 2: Operating Expenses */}
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    Gross Expenses
                  </span>
                  <span className="text-slate-500 text-xs font-semibold">Outflow</span>
                </div>
                <div className="mt-2.5">
                  <div className="text-2xl font-semibold text-slate-900 tracking-tight">
                    {formatCurrency(summary.total_expenses)}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1">
                    Operating expenditures before refunds
                  </div>
                </div>
              </div>

              {/* Card 3: Refunds & Credits */}
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    Refunds & Credits
                  </span>
                  <span className="text-slate-500 text-xs font-semibold">Credit</span>
                </div>
                <div className="mt-2.5">
                  <div className="text-2xl font-semibold text-slate-900 tracking-tight">
                    {formatCurrency(summary.total_refunds)}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1">
                    {summary.unmatched_refunds && parseFloat(summary.unmatched_refunds) > 0 ? (
                      <span>
                        <span className="text-emerald-700 font-medium">{formatCurrency(summary.matched_refunds)}</span> applied (Net exp: {formatCurrency(summary.net_expenses)})
                        <br />
                        <span className="text-amber-700 font-medium">⚠️ {formatCurrency(summary.unmatched_refunds)} unverified</span>
                      </span>
                    ) : (
                      <span>Applied against expenses (Net: {formatCurrency(summary.net_expenses)})</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Card 4: Operating Result (Provisional vs Reconciled) */}
              <div className={`p-4 rounded-xl border shadow-sm transition ${
                summary.is_provisional
                  ? "bg-amber-50/30 border-amber-300"
                  : "bg-white border-slate-200"
              }`}>
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-600">
                    {summary.is_provisional ? "Provisional Result" : "Operating Result"}
                  </span>
                  <span className={`text-[10px] font-medium px-2 py-0.5 rounded ${
                    summary.is_provisional
                      ? "bg-amber-100 text-amber-900 border border-amber-300"
                      : "bg-emerald-100 text-emerald-800 border border-emerald-200"
                  }`}>
                    {summary.is_provisional ? "Provisional" : "Reconciled"}
                  </span>
                </div>
                <div className="mt-2.5">
                  <div className={`text-2xl font-semibold tracking-tight ${
                    parseFloat(summary.net_operating_result) >= 0 ? "text-emerald-700" : "text-rose-700"
                  }`}>
                    {formatCurrency(summary.net_operating_result)}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1">
                    {summary.is_provisional ? (
                      <span className="text-amber-800">
                        {summary.needs_review_count} item{summary.needs_review_count > 1 ? "s" : ""} pending review
                      </span>
                    ) : (
                      <span>Revenue − Net Expenses − Fees</span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Secondary Financial Metrics Strip */}
            <div className="flex flex-wrap items-center justify-between gap-4 bg-white px-4 py-2.5 rounded-lg border border-slate-200 text-xs text-slate-600">
              <div className="flex flex-wrap items-center gap-5">
                <span>
                  <strong className="text-slate-800">Total Entries:</strong> {summary.transaction_count}
                </span>
                <span>
                  <strong className="text-slate-800">Internal Transfers:</strong>{" "}
                  {formatCurrency(summary.total_transfers)}{" "}
                  <span className="text-slate-400 font-normal">(Excluded from P&L)</span>
                </span>
                <span>
                  <strong className="text-slate-800">Fees (Bank/Stripe):</strong>{" "}
                  {formatCurrency(summary.total_fees)}
                </span>
                {summary.duplicate_count && summary.duplicate_count > 0 ? (
                  <span className="text-rose-700 font-medium">
                    ⚠️ {summary.duplicate_count} potential duplicate{summary.duplicate_count > 1 ? "s" : ""} flagged
                  </span>
                ) : null}
              </div>

              <div>
                {summary.needs_review_count > 0 ? (
                  <span className="text-amber-800 text-[11px] font-medium">
                    ⚠️ {summary.needs_review_count} unresolved item{summary.needs_review_count > 1 ? "s" : ""} ({formatCurrency(summary.unclassified_amount)}) may alter final results
                  </span>
                ) : (
                  <span className="text-emerald-700 text-[11px] font-medium">
                    ✓ All statement entries verified
                  </span>
                )}
              </div>
            </div>

            {/* Filter & Search Bar */}
            <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {/* Search */}
                <div>
                  <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
                    Search Description / Amount
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="e.g. Adobe, Uber, $54.99..."
                      className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-800 focus:border-slate-800"
                    />
                    <svg className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                </div>

                {/* Status Segment Filter */}
                <div>
                  <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
                    Review Status
                  </label>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-800 bg-white"
                  >
                    <option value="all">All Items ({statusCounts.all})</option>
                    <option value="needs_review">Needs Review ({statusCounts.needs_review})</option>
                    <option value="auto">Auto Categorized ({statusCounts.auto})</option>
                    <option value="user_confirmed">User Confirmed ({statusCounts.user_confirmed})</option>
                    <option value="user_corrected">User Corrected ({statusCounts.user_corrected})</option>
                  </select>
                </div>

                {/* Category Filter */}
                <div>
                  <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
                    Business Category
                  </label>
                  <select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-800 bg-white"
                  >
                    <option value="all">All Categories</option>
                    {BUSINESS_CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Financial Treatment Filter */}
                <div>
                  <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
                    Accounting Type
                  </label>
                  <select
                    value={typeFilter}
                    onChange={(e) => setTypeFilter(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-800 bg-white"
                  >
                    <option value="all">All Types</option>
                    {TRANSACTION_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-100">
                <span>
                  Showing <strong className="text-slate-800">{filteredTransactions.length}</strong> of {transactions.length} transactions
                </span>
                {(searchQuery || statusFilter !== "all" || categoryFilter !== "all" || typeFilter !== "all") && (
                  <button
                    onClick={() => {
                      setSearchQuery("");
                      setStatusFilter("all");
                      setCategoryFilter("all");
                      setTypeFilter("all");
                    }}
                    className="text-slate-900 hover:underline font-medium"
                  >
                    Reset Filters
                  </button>
                )}
              </div>
            </div>

            {/* Transactions Ledger Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                  <thead className="bg-slate-50/80 text-slate-600 font-semibold uppercase text-[10px] tracking-wider">
                    <tr>
                      <th className="px-3.5 py-2.5">Date</th>
                      <th className="px-3.5 py-2.5">Description</th>
                      <th className="px-3.5 py-2.5 text-right">Amount</th>
                      <th className="px-3.5 py-2.5">Type</th>
                      <th className="px-3.5 py-2.5">Category</th>
                      <th className="px-3.5 py-2.5">Status</th>
                      <th className="px-3.5 py-2.5">Rule / Confidence</th>
                      <th className="px-3.5 py-2.5 text-center">Resolution</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {filteredTransactions.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="px-6 py-12 text-center text-slate-400 italic">
                          No transactions match the selected filter criteria.
                        </td>
                      </tr>
                    ) : (
                      filteredTransactions.map((tx) => {
                        const amountNum = parseFloat(tx.amount);
                        const isIncome = tx.transaction_type === "income";
                        const isRefund = tx.transaction_type === "refund";
                        const isTransfer = tx.transaction_type === "transfer";
                        const isFee = tx.transaction_type === "fee";

                        return (
                          <tr
                            key={tx.id}
                            className={`hover:bg-slate-50/80 transition ${
                              tx.review_status === "needs_review" ? "bg-amber-50/30" : ""
                            }`}
                          >
                            {/* Date */}
                            <td className="px-3.5 py-2.5 whitespace-nowrap font-mono text-[11px] text-slate-600">
                              {tx.date}
                            </td>

                            {/* Description */}
                            <td className="px-3.5 py-2.5 max-w-xs">
                              <div className="font-medium text-slate-900 truncate" title={tx.description}>
                                {tx.description}
                              </div>
                              <div className="flex flex-wrap items-center gap-1.5 mt-0.5">
                                {tx.is_possible_duplicate && (
                                  <span className="inline-flex items-center text-[10px] font-medium px-1.5 py-0.2 rounded bg-rose-50 text-rose-700 border border-rose-200">
                                    Duplicate (Group {tx.duplicate_group_id})
                                  </span>
                                )}
                                {tx.linked_transaction_id && (
                                  <span className="inline-flex items-center text-[10px] font-medium px-1.5 py-0.2 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                                    Linked to #{tx.linked_transaction_id}
                                  </span>
                                )}
                              </div>
                            </td>

                            {/* Amount */}
                            <td className="px-3.5 py-2.5 whitespace-nowrap text-right font-mono text-xs font-medium tabular-nums">
                              <span
                                className={
                                  isIncome
                                    ? "text-emerald-700 font-semibold"
                                    : isRefund
                                    ? "text-amber-700"
                                    : isTransfer
                                    ? "text-slate-600 font-medium"
                                    : isFee
                                    ? "text-slate-600"
                                    : amountNum < 0
                                    ? "text-slate-900"
                                    : "text-slate-800"
                                }
                              >
                                {amountNum > 0 ? `+${tx.amount}` : tx.amount}
                              </span>
                            </td>

                            {/* Type Selector */}
                            <td className="px-3.5 py-2.5 whitespace-nowrap">
                              <select
                                value={tx.transaction_type}
                                onChange={(e) =>
                                  handleUpdateTransaction(
                                    tx.id,
                                    "transaction_type",
                                    e.target.value as TransactionType
                                  )
                                }
                                className="px-2 py-1 text-[11px] border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-800 bg-white"
                              >
                                {TRANSACTION_TYPES.map((t) => (
                                  <option key={t.value} value={t.value}>
                                    {t.label}
                                  </option>
                                ))}
                              </select>
                            </td>

                            {/* Category Selector */}
                            <td className="px-3.5 py-2.5 whitespace-nowrap">
                              <select
                                value={tx.business_category}
                                onChange={(e) =>
                                  handleUpdateTransaction(
                                    tx.id,
                                    "business_category",
                                    e.target.value as BusinessCategory
                                  )
                                }
                                className="px-2 py-1 text-[11px] border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-800 bg-white max-w-[140px]"
                              >
                                {BUSINESS_CATEGORIES.map((cat) => (
                                  <option key={cat} value={cat}>
                                    {cat}
                                  </option>
                                ))}
                              </select>
                            </td>

                            {/* Status Badge */}
                            <td className="px-3.5 py-2.5 whitespace-nowrap">
                              {tx.review_status === "needs_review" && (
                                <span className="inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
                                  Needs Review
                                </span>
                              )}
                              {tx.review_status === "auto" && (
                                <span className="inline-flex items-center text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                                  Auto
                                </span>
                              )}
                              {tx.review_status === "user_confirmed" && (
                                <span className="inline-flex items-center text-[10px] font-medium px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                                  Verified
                                </span>
                              )}
                              {tx.review_status === "user_corrected" && (
                                <span className="inline-flex items-center text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-300">
                                  Edited
                                </span>
                              )}
                            </td>

                            {/* Rule / Confidence */}
                            <td className="px-3.5 py-2.5 max-w-xs">
                              <div className="flex items-center gap-1.5">
                                <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200">
                                  {tx.rule_id}
                                </span>
                                <span
                                  className={`text-[10px] font-medium ${
                                    tx.confidence === "high"
                                      ? "text-emerald-700"
                                      : tx.confidence === "medium"
                                      ? "text-slate-600"
                                      : "text-amber-700"
                                  }`}
                                >
                                  {tx.confidence} conf.
                                </span>
                              </div>
                              <div className="text-[11px] text-slate-500 truncate mt-0.5" title={tx.explanation}>
                                {tx.explanation}
                              </div>
                            </td>

                            {/* Quick Action */}
                            <td className="px-3.5 py-2.5 whitespace-nowrap text-center">
                              {tx.review_status === "needs_review" ? (
                                <button
                                  onClick={() => handleConfirmTransaction(tx.id)}
                                  className="px-2.5 py-1 text-[11px] font-medium bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 rounded shadow-sm transition"
                                  title="Confirm classification"
                                >
                                  Approve
                                </button>
                              ) : (
                                <span className="text-slate-300 text-xs">—</span>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Category Aggregates Section */}
            {summary.category_totals && Object.keys(summary.category_totals).length > 0 && (
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                    Expenditure by Business Category
                  </h3>
                  <span className="text-[11px] text-slate-400">
                    {Object.keys(summary.category_totals).length} Active Categories
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
                  {Object.entries(summary.category_totals).map(([category, amount]) => (
                    <div key={category} className="p-2.5 rounded-lg bg-slate-50/80 border border-slate-200/60">
                      <div className="text-[11px] text-slate-500 font-medium truncate" title={category}>
                        {category}
                      </div>
                      <div className="text-sm font-semibold text-slate-900 mt-0.5 tabular-nums">
                        {formatCurrency(amount)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Professional Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 text-center text-[11px] text-slate-400">
          Statement Reconciler &middot; Business Ledger &amp; Tax Statement Classification Tool
        </div>
      </footer>
    </div>
  );
}
