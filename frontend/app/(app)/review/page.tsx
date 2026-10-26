"use client";

import { useState, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, SkipForward, Undo2 } from "lucide-react";
import { api } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type { Transaction, Category } from "@/lib/types";
import { formatDate, formatConfidence } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Amount } from "@/components/ui/amount";
import { toast } from "sonner";

function ProgressRing({ done, total }: { done: number; total: number }) {
  const r = 28;
  const circ = 2 * Math.PI * r;
  const pct = total > 0 ? done / total : 0;
  return (
    <svg width={72} height={72} viewBox="0 0 72 72">
      <circle cx={36} cy={36} r={r} fill="none" strokeWidth={5} stroke="var(--border)" />
      <motion.circle
        cx={36} cy={36} r={r} fill="none" strokeWidth={5}
        stroke="var(--accent)"
        strokeLinecap="round"
        strokeDasharray={circ}
        animate={{ strokeDashoffset: circ * (1 - pct) }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        style={{ transform: "rotate(-90deg)", transformOrigin: "center" }}
      />
      <text x={36} y={40} textAnchor="middle" fontSize={13} fontWeight={600} fill="var(--fg)">
        {done}/{total}
      </text>
    </svg>
  );
}

export default function ReviewPage() {
  const qc = useQueryClient();
  const [index, setIndex] = useState(0);
  const [done, setDone] = useState(0);
  const [pickedCat, setPickedCat] = useState("");
  const [finished, setFinished] = useState(false);
  const [lastConfirmed, setLastConfirmed] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: qk.reviewQueue(),
    queryFn: () => api.get("/review/queue") as Promise<{ items: Transaction[]; total: number }>,
  });
  const items = data?.items ?? [];

  const { data: categoriesData = [] } = useQuery({
    queryKey: qk.categories(),
    queryFn: () => api.get("/categories") as Promise<Category[]>,
  });

  const expenseCategories = categoriesData.filter((c) => c.group === "expense");
  const incomeCategories = categoriesData.filter((c) => c.group === "income");

  const current = items[index];
  const suggestedCat = current ? categoriesData.find((c) => c.id === current.category_id) ?? null : null;

  useEffect(() => {
    if (current) setPickedCat(current.category_id ?? "");
  }, [current]);

  useEffect(() => {
    if (items.length > 0 && index >= items.length) setFinished(true);
  }, [index, items.length]);

  const confirm = useMutation({
    mutationFn: (catId: string) =>
      api.patch(`/transactions/${current.id}`, {
        category_id: catId || current.category_id,
        status: "confirmed",
      }),
    onSuccess: (_, catId) => {
      setLastConfirmed(current.id);
      setDone((d) => d + 1);
      setIndex((i) => i + 1);
      qc.invalidateQueries({ queryKey: qk.dashboard() });
      const name = categoriesData.find((c) => c.id === (catId || current.category_id))?.name;
      toast.success(name ? `Confirmed as ${name}` : "Confirmed");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const undo = useMutation({
    mutationFn: () => api.post(`/transactions/${lastConfirmed}/undo`),
    onSuccess: () => {
      setDone((d) => Math.max(0, d - 1));
      setIndex((i) => Math.max(0, i - 1));
      setFinished(false);
      setLastConfirmed(null);
      qc.invalidateQueries({ queryKey: qk.dashboard() });
    },
  });

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!current) return;
      const num = parseInt(e.key);
      if (num >= 1 && num <= 9 && expenseCategories[num - 1]) {
        setPickedCat(expenseCategories[num - 1].id);
      }
      if (e.key === "Enter") confirm.mutate(pickedCat);
      if (e.key === "s" || e.key === "S") setIndex((i) => i + 1);
      if ((e.key === "z" || e.key === "Z") && lastConfirmed) undo.mutate();
    },
    [current, expenseCategories, pickedCat, lastConfirmed, confirm, undo]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 rounded-full border-2 border-[var(--accent)] border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!current || items.length === 0 || finished) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8">
        <motion.div
          initial={{ scale: 0, rotate: -12 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: "spring", damping: 11 }}
          className="w-24 h-24 rounded-full flex items-center justify-center mb-6"
          style={{ background: "var(--accent-light)" }}
        >
          <CheckCircle size={40} style={{ color: "var(--accent)" }} />
        </motion.div>
        <h2 className="text-2xl font-bold mb-2" style={{ fontFamily: "var(--font-display)" }}>
          Queue cleared!
        </h2>
        <p className="text-[var(--fg-muted)]">
          {done > 0 ? `You reviewed ${done} transaction${done !== 1 ? "s" : ""}.` : "All transactions have been reviewed."}
        </p>
        <Button className="mt-6" onClick={() => (window.location.href = "/dashboard")}>
          Back to Dashboard
        </Button>
      </div>
    );
  }

  const txn = current;

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold" style={{ fontFamily: "var(--font-display)" }}>Review Queue</h1>
          <p className="text-sm text-[var(--fg-muted)]">Keyboard: 1-9 pick category, Enter confirm, S skip, Z undo</p>
        </div>
        <ProgressRing done={done} total={items.length} />
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={txn.id}
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -40 }}
          transition={{ duration: 0.2 }}
        >
          {/* Transaction card */}
          <div
            className="rounded-[var(--radius-xl)] border p-6 mb-4"
            style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "var(--shadow-md)" }}
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="text-xs text-[var(--fg-muted)]">{formatDate(txn.posted_date)}</div>
                <div className="text-xl font-semibold mt-1" style={{ fontFamily: "var(--font-display)" }}>
                  {txn.merchant || txn.description_raw}
                </div>
              </div>
              <div className="text-2xl font-bold tabular">
                <Amount cents={txn.amount_cents} />
              </div>
            </div>

            {txn.review_reason && (
              <div
                className="rounded-[var(--radius-md)] px-3 py-2 text-sm mb-4 highlight-row"
                style={{ background: "var(--highlight-bg)", color: "var(--highlight-fg)", borderLeft: "3px solid var(--highlight)" }}
              >
                {txn.review_reason}
              </div>
            )}

            {suggestedCat && (
              <div className="flex items-center gap-2 text-sm mb-4">
                <span className="text-[var(--fg-muted)]">Suggested:</span>
                <Badge variant="auto">{suggestedCat.name}</Badge>
                <span className="text-[var(--fg-faint)]">({formatConfidence(txn.confidence ?? 0)})</span>
              </div>
            )}

            {txn.reasons && txn.reasons.length > 0 && (
              <details className="text-xs text-[var(--fg-muted)] mt-2">
                <summary className="cursor-pointer hover:text-[var(--fg)]">View reason trail</summary>
                <ol className="mt-2 space-y-1 pl-4">
                  {txn.reasons.map((r, i) => <li key={i}>{i + 1}. {r}</li>)}
                </ol>
              </details>
            )}
          </div>

          {/* Category grid */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            {expenseCategories.slice(0, 9).map((cat, i) => (
              <button
                key={cat.id}
                onClick={() => setPickedCat(cat.id)}
                className="flex items-center gap-2 rounded-[var(--radius-md)] border px-3 py-2 text-xs text-left transition-all"
                style={{
                  background: pickedCat === cat.id ? "var(--accent-light)" : "var(--surface)",
                  borderColor: pickedCat === cat.id ? "var(--accent)" : "var(--border)",
                  color: pickedCat === cat.id ? "var(--accent)" : "var(--fg)",
                }}
              >
                <span className="text-[var(--fg-faint)] font-mono">{i + 1}</span>
                <span className="truncate">{cat.name}</span>
              </button>
            ))}
          </div>

          {/* Also show income categories */}
          <div className="flex flex-wrap gap-2 mb-6">
            {incomeCategories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setPickedCat(cat.id)}
                className="rounded-full border px-3 py-1 text-xs transition-all"
                style={{
                  background: pickedCat === cat.id ? "var(--accent-light)" : "transparent",
                  borderColor: pickedCat === cat.id ? "var(--accent)" : "var(--border)",
                  color: pickedCat === cat.id ? "var(--accent)" : "var(--fg-muted)",
                }}
              >
                {cat.name}
              </button>
            ))}
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <Button
              className="flex-1"
              onClick={() => confirm.mutate(pickedCat)}
              disabled={confirm.isPending}
            >
              <CheckCircle size={16} />
              Confirm {pickedCat ? `as ${categoriesData.find((c) => c.id === pickedCat)?.name}` : "suggestion"}
            </Button>
            <Button variant="outline" onClick={() => setIndex((i) => i + 1)}>
              <SkipForward size={16} /> Skip
            </Button>
            {lastConfirmed && (
              <Button variant="ghost" onClick={() => undo.mutate()} disabled={undo.isPending}>
                <Undo2 size={16} />
              </Button>
            )}
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
