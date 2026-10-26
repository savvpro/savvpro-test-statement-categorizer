"use client";

import type { SummaryItem } from "@/lib/api";
import CategoryBadge from "./CategoryBadge";

interface CategorySummaryProps {
  summary: SummaryItem[];
}

export default function CategorySummary({ summary }: CategorySummaryProps) {
  const totalExpenses = summary
    .filter((s) => s.total < 0)
    .reduce((acc, s) => acc + Math.abs(s.total), 0);

  const sorted = [...summary].sort((a, b) => a.total - b.total);

  return (
    <div className="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="border-b border-gray-100 px-5 py-4">
        <h2 className="text-sm font-semibold text-gray-700">Category Summary</h2>
        <p className="mt-0.5 text-xs text-gray-500">
          Total categorised expenses:{" "}
          <span className="font-semibold text-gray-800">
            ${totalExpenses.toFixed(2)}
          </span>
        </p>
      </div>

      <ul className="divide-y divide-gray-50">
        {sorted.map((item) => {
          const isCredit = item.total > 0;
          const pct =
            totalExpenses > 0 && !isCredit
              ? Math.round((Math.abs(item.total) / totalExpenses) * 100)
              : null;

          return (
            <li key={item.category} className="flex items-center gap-3 px-5 py-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <CategoryBadge category={item.category} />
                  <span className="text-xs text-gray-400">× {item.count}</span>
                </div>
                {pct !== null && (
                  <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-gray-100">
                    <div
                      className="h-full rounded-full bg-brand-500 transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                )}
              </div>
              <span
                className={
                  isCredit
                    ? "text-sm font-semibold text-emerald-600"
                    : "text-sm font-semibold text-gray-800"
                }
              >
                {isCredit ? "+" : ""}${Math.abs(item.total).toFixed(2)}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
