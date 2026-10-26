"use client";

import { useState, useCallback, useEffect } from "react";
import FileUpload from "@/components/FileUpload";
import TransactionTable from "@/components/TransactionTable";
import CategorySummary from "@/components/CategorySummary";
import {
  uploadStatement,
  overrideCategory,
  getSummary,
  getCategories,
  type Transaction,
  type SummaryItem,
} from "@/lib/api";

type AppState = "idle" | "loading" | "done" | "error";

export default function HomePage() {
  const [state, setState] = useState<AppState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<SummaryItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);

  // Load available categories once on mount
  useEffect(() => {
    getCategories()
      .then(setCategories)
      .catch(() => {
        // Fallback list in case the backend is not yet running
        setCategories([
          "Software & Subscriptions",
          "Travel & Transport",
          "Food & Dining",
          "Office & Supplies",
          "Marketing & Advertising",
          "Education & Training",
          "Professional Services",
          "Health & Wellness",
          "Transfer / Non-Expense",
          "Needs Review",
        ]);
      });
  }, []);

  const handleUpload = useCallback(async (file: File) => {
    setState("loading");
    setError(null);

    try {
      const res = await uploadStatement(file);
      setSessionId(res.filename);
      setTransactions(res.transactions);

      const summaryRes = await getSummary(res.filename);
      setSummary(summaryRes.summary);

      setState("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setState("error");
    }
  }, []);

  const handleOverride = useCallback(
    async (id: string, category: string) => {
      if (!sessionId) return;

      const updated = await overrideCategory(sessionId, id, category);
      setTransactions((prev) =>
        prev.map((t) => (t.id === updated.id ? updated : t))
      );

      // Refresh summary
      const summaryRes = await getSummary(sessionId);
      setSummary(summaryRes.summary);
    },
    [sessionId]
  );

  const handleReset = () => {
    setState("idle");
    setSessionId(null);
    setTransactions([]);
    setSummary([]);
    setError(null);
  };

  const reviewCount = transactions.filter((t) => t.is_review).length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500 text-white font-bold text-sm">
              SC
            </div>
            <span className="text-base font-semibold text-gray-900">
              Statement Categorizer
            </span>
          </div>

          {state === "done" && (
            <button
              onClick={handleReset}
              className="rounded-full border border-gray-300 px-4 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
            >
              ← Upload another
            </button>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-10">
        {/* Hero */}
        {state === "idle" && (
          <div className="flex flex-col items-center text-center mb-10">
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              Tax-ready in minutes
            </h1>
            <p className="mt-3 max-w-xl text-sm text-gray-500">
              Upload your bank or credit-card statement and every transaction
              gets sorted automatically — software, travel, food, and more.
              Review and fix anything the app isn&apos;t sure about.
            </p>
          </div>
        )}

        {/* Upload zone */}
        {(state === "idle" || state === "loading" || state === "error") && (
          <div className="mx-auto max-w-lg">
            <FileUpload onUpload={handleUpload} loading={state === "loading"} />
            {state === "error" && error && (
              <p className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">
                {error}
              </p>
            )}
            <p className="mt-4 text-center text-xs text-gray-400">
              Uses fake sample data only. Never upload real personal bank statements.
            </p>
          </div>
        )}

        {/* Results */}
        {state === "done" && (
          <div className="space-y-6">
            {/* Stats bar */}
            <div className="flex flex-wrap gap-4">
              <div className="rounded-xl border border-gray-200 bg-white px-5 py-3 shadow-sm">
                <p className="text-xs font-medium text-gray-500">Transactions</p>
                <p className="mt-0.5 text-2xl font-bold text-gray-900">
                  {transactions.length}
                </p>
              </div>
              <div className="rounded-xl border border-gray-200 bg-white px-5 py-3 shadow-sm">
                <p className="text-xs font-medium text-gray-500">Auto-categorised</p>
                <p className="mt-0.5 text-2xl font-bold text-emerald-600">
                  {transactions.length - reviewCount}
                </p>
              </div>
              {reviewCount > 0 && (
                <div className="rounded-xl border border-red-100 bg-red-50 px-5 py-3">
                  <p className="text-xs font-medium text-red-500">Needs Review</p>
                  <p className="mt-0.5 text-2xl font-bold text-red-600">
                    {reviewCount}
                  </p>
                </div>
              )}
            </div>

            {/* Main layout: table + sidebar */}
            <div className="flex flex-col gap-6 lg:flex-row">
              <div className="flex-1 min-w-0">
                <TransactionTable
                  transactions={transactions}
                  categories={categories}
                  sessionId={sessionId!}
                  onOverride={handleOverride}
                />
              </div>
              <div className="w-full lg:w-72 shrink-0">
                <CategorySummary summary={summary} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
