"use client";

import { useState, useCallback } from "react";
import clsx from "clsx";
import type { Transaction } from "@/lib/api";
import CategoryBadge from "./CategoryBadge";

interface TransactionTableProps {
  transactions: Transaction[];
  categories: string[];
  sessionId: string;
  onOverride: (id: string, category: string) => Promise<void>;
}

type FilterMode = "all" | "review";

export default function TransactionTable({
  transactions,
  categories,
  sessionId,
  onOverride,
}: TransactionTableProps) {
  const [filter, setFilter] = useState<FilterMode>("all");
  const [saving, setSaving] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const reviewCount = transactions.filter((t) => t.is_review).length;

  const visible = transactions.filter((t) => {
    if (filter === "review" && !t.is_review) return false;
    if (search && !t.description.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const handleCategoryChange = useCallback(
    async (id: string, category: string) => {
      setSaving(id);
      try {
        await onOverride(id, category);
      } finally {
        setSaving(null);
      }
    },
    [onOverride]
  );

  return (
    <div className="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      {/* Toolbar */}
      <div className="flex flex-col gap-3 border-b border-gray-100 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-2">
          <button
            onClick={() => setFilter("all")}
            className={clsx(
              "rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors",
              filter === "all"
                ? "bg-gray-900 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            )}
          >
            All ({transactions.length})
          </button>
          <button
            onClick={() => setFilter("review")}
            className={clsx(
              "rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors",
              filter === "review"
                ? "bg-red-600 text-white"
                : "bg-red-50 text-red-600 hover:bg-red-100"
            )}
          >
            Needs Review ({reviewCount})
          </button>
        </div>

        <input
          type="search"
          placeholder="Search description…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 sm:w-56"
        />
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              <th className="px-5 py-3">Date</th>
              <th className="px-5 py-3">Description</th>
              <th className="px-5 py-3 text-right">Amount</th>
              <th className="px-5 py-3">Category</th>
              <th className="px-5 py-3">Confidence</th>
              <th className="px-5 py-3">Override</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {visible.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-10 text-center text-sm text-gray-400">
                  No transactions match the current filter.
                </td>
              </tr>
            )}
            {visible.map((txn) => (
              <tr
                key={txn.id}
                className={clsx(
                  "txn-row",
                  txn.is_review ? "bg-red-50/40" : "bg-white hover:bg-gray-50"
                )}
              >
                <td className="whitespace-nowrap px-5 py-3 text-gray-500 font-mono text-xs">
                  {txn.date ?? "—"}
                </td>
                <td className="px-5 py-3 font-medium text-gray-800">
                  <span title={txn.reason}>{txn.description}</span>
                  {txn.original_category && (
                    <span className="ml-2 text-xs text-gray-400 line-through">
                      {txn.original_category}
                    </span>
                  )}
                </td>
                <td
                  className={clsx(
                    "whitespace-nowrap px-5 py-3 text-right font-mono font-medium",
                    txn.amount !== null && txn.amount > 0
                      ? "text-emerald-600"
                      : "text-gray-800"
                  )}
                >
                  {txn.amount !== null
                    ? `${txn.amount < 0 ? "-" : "+"}$${Math.abs(txn.amount).toFixed(2)}`
                    : "—"}
                </td>
                <td className="px-5 py-3">
                  <CategoryBadge category={txn.category} isReview={txn.is_review} />
                </td>
                <td className="px-5 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-200">
                      <div
                        className={clsx(
                          "h-full rounded-full transition-all",
                          txn.confidence >= 0.8
                            ? "bg-emerald-500"
                            : txn.confidence >= 0.5
                            ? "bg-yellow-400"
                            : "bg-red-400"
                        )}
                        style={{ width: `${Math.round(txn.confidence * 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400">
                      {Math.round(txn.confidence * 100)}%
                    </span>
                  </div>
                </td>
                <td className="px-5 py-3">
                  <div className="flex items-center gap-1">
                    <select
                      disabled={saving === txn.id}
                      defaultValue={txn.category}
                      onChange={(e) => handleCategoryChange(txn.id, e.target.value)}
                      className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
                    >
                      {categories.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat}
                        </option>
                      ))}
                    </select>
                    {saving === txn.id && (
                      <svg
                        className="h-3.5 w-3.5 animate-spin text-brand-500"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8v8H4z"
                        />
                      </svg>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
