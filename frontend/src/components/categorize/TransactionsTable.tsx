"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { money, percent, shortDate } from "@/lib/format";
import { NEEDS_REVIEW, type Category, type Transaction } from "@/lib/types";

type Tab = "review" | "all";

function toneFor(tx: Transaction, categories: Category[]) {
  if (tx.category === NEEDS_REVIEW) return "amber" as const;
  const kind = categories.find((c) => c.name === tx.category)?.kind;
  if (kind === "income") return "green" as const;
  if (kind === "not_spending") return "violet" as const;
  if (kind === "refund") return "blue" as const;
  return categories.find((c) => c.name === tx.category)?.deductible ? ("blue" as const) : ("slate" as const);
}

export function TransactionsTable({
  transactions,
  categories,
  onFix,
}: {
  transactions: Transaction[];
  categories: Category[];
  onFix: (id: number, category: string, applyToSimilar: boolean) => Promise<void>;
}) {
  const reviewCount = transactions.filter((t) => t.category === NEEDS_REVIEW).length;
  const [tab, setTabState] = useState<Tab>(reviewCount ? "review" : "all");
  // The open tab lives in the address bar too, so a refresh keeps it.
  useEffect(() => {
    const saved = new URLSearchParams(window.location.search).get("view");
    if (saved === "review" || saved === "all") setTabState(saved);
  }, []);
  const setTab = (t: Tab) => {
    setTabState(t);
    const url = new URL(window.location.href);
    url.searchParams.set("view", t);
    window.history.replaceState(null, "", url);
  };
  // Newest first, whatever order the bank exported them in.
  const sorted = [...transactions].sort((a, b) => b.date.localeCompare(a.date) || a.row - b.row);
  const rows = tab === "review" ? sorted.filter((t) => t.category === NEEDS_REVIEW) : sorted;

  return (
    <div className="overflow-hidden rounded-2xl bg-white shadow-card ring-1 ring-brand-100">
      <div className="flex flex-wrap items-center gap-2 border-b border-brand-100 px-5 py-3">
        {(["review", "all"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium ${tab === t ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-brand-50"}`}
          >
            {t === "review" ? `Needs review (${reviewCount})` : `All transactions (${transactions.length})`}
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <p className="px-5 py-12 text-center text-sm text-slate-500">Nothing left to review. Every row has a category.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-brand-50/60 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-5 py-3 font-medium">Date</th>
                <th className="px-5 py-3 font-medium">Description</th>
                <th className="px-5 py-3 text-right font-medium">Amount</th>
                <th className="px-5 py-3 font-medium">Category &amp; reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((tx) => (
                <Row key={tx.id} tx={tx} categories={categories} tone={toneFor(tx, categories)} onFix={onFix} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Row({
  tx,
  categories,
  tone,
  onFix,
}: {
  tx: Transaction;
  categories: Category[];
  tone: ReturnType<typeof toneFor>;
  onFix: (id: number, category: string, applyToSimilar: boolean) => Promise<void>;
}) {
  const review = tx.category === NEEDS_REVIEW;
  const [editing, setEditing] = useState(false);
  const [choice, setChoice] = useState(tx.suggestion ?? (review ? "" : tx.category));
  const [similar, setSimilar] = useState(true);
  const [saving, setSaving] = useState(false);
  const amount = Number(tx.amount);

  const save = async () => {
    if (!choice) return;
    setSaving(true);
    try {
      await onFix(tx.id, choice, similar);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <tr className={review ? "bg-amber-50/40" : ""}>
      <td className="whitespace-nowrap px-5 py-3 text-slate-500">{shortDate(tx.date)}</td>
      <td className="px-5 py-3">
        <p className="font-mono text-xs text-slate-700">{tx.description}</p>
        {tx.pending && <span className="text-xs text-amber-700">Pending</span>}
      </td>
      <td className={`whitespace-nowrap px-5 py-3 text-right font-semibold tabular-nums ${amount > 0 ? "text-emerald-600" : "text-slate-800"}`}>
        {amount > 0 ? "+" : ""}
        {money(amount)}
      </td>
      <td className="min-w-[280px] px-5 py-3">
        {review || editing ? (
          <div className="flex flex-col gap-2">
            <p className="text-xs text-amber-800">{tx.reason}</p>
            <div className="flex flex-wrap items-center gap-2">
              <select
                aria-label={`Category for ${tx.description}`}
                value={choice}
                onChange={(e) => setChoice(e.target.value)}
                className="rounded-md border border-brand-200 bg-white px-2 py-1.5 text-sm"
              >
                <option value="" disabled>
                  Choose a category…
                </option>
                {categories.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name}
                    {c.name === tx.suggestion ? " (suggested)" : ""}
                  </option>
                ))}
              </select>
              <Button className="px-3 py-1.5" disabled={!choice || saving} onClick={save}>
                {saving ? "Saving…" : "Save"}
              </Button>
              {editing && (
                <Button variant="ghost" className="px-2 py-1.5" onClick={() => setEditing(false)}>
                  Cancel
                </Button>
              )}
            </div>
            <label className="flex items-center gap-2 text-xs text-slate-600">
              <input type="checkbox" checked={similar} onChange={(e) => setSimilar(e.target.checked)} />
              Also apply to other unsure rows from {tx.merchant || "this merchant"}
            </label>
          </div>
        ) : (
          <div className="flex items-start justify-between gap-3">
            <div>
              <Badge tone={tone}>{tx.category}</Badge>
              <p className="mt-1 text-xs text-slate-500">
                {tx.reason}
                {tx.refund_of ? ` · reduces ${tx.refund_of}` : ""} · {percent(tx.confidence)} sure
              </p>
            </div>
            <button onClick={() => setEditing(true)} className="text-xs font-medium text-brand-600 hover:text-brand-700">
              Change
            </button>
          </div>
        )}
      </td>
    </tr>
  );
}
