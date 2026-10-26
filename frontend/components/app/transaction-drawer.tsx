"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X, RotateCcw, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type { Transaction, Category } from "@/lib/types";
import { formatDate, formatConfidence } from "@/lib/format";
import { Amount } from "@/components/ui/amount";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { toast } from "sonner";

interface TransactionDrawerProps {
  transaction: Transaction | null;
  onClose: () => void;
}

export function TransactionDrawer({ transaction, onClose }: TransactionDrawerProps) {
  const qc = useQueryClient();
  const [selectedCategory, setSelectedCategory] = useState(transaction?.category_id ?? "");
  const [note, setNote] = useState(transaction?.note ?? "");
  const [applyToSimilar, setApplyToSimilar] = useState(false);
  const [createRule, setCreateRule] = useState(false);

  const { data: categories = [] } = useQuery({
    queryKey: qk.categories(),
    queryFn: () => api.get("/categories") as Promise<Category[]>,
  });

  const patchMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.patch(`/transactions/${transaction!.id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.transactions() });
      qc.invalidateQueries({ queryKey: qk.reviewQueue() });
      qc.invalidateQueries({ queryKey: qk.dashboard() });
      toast.success("Transaction updated");
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const undoMutation = useMutation({
    mutationFn: () => api.post(`/transactions/${transaction!.id}/undo`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.transactions() });
      toast.success("Correction undone");
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function handleSave() {
    patchMutation.mutate({
      category_id: selectedCategory || null,
      note: note || null,
      status: "confirmed",
      apply_to_similar: applyToSimilar,
      create_rule: createRule,
    });
  }

  return (
    <AnimatePresence>
      {transaction && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.4 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black"
            onClick={onClose}
          />
          <motion.aside
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-md overflow-y-auto flex flex-col"
            style={{ background: "var(--surface)", borderLeft: "1px solid var(--border)" }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: "var(--border)" }}>
              <div>
                <h2 className="font-semibold text-[var(--fg)]">{transaction.merchant}</h2>
                <p className="text-xs text-[var(--fg-muted)]">{formatDate(transaction.posted_date)}</p>
              </div>
              <button onClick={onClose} className="text-[var(--fg-muted)] hover:text-[var(--fg)] transition-colors p-1">
                <X size={18} />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 p-6 space-y-6">
              {/* Amount + Status */}
              <div className="flex items-center justify-between">
                <Amount cents={transaction.amount_cents} className="text-2xl" />
                <Badge variant={transaction.status === "needs_review" ? "review" : transaction.status === "confirmed" ? "confirmed" : "auto"}>
                  {transaction.status === "needs_review" ? "Needs Review" : transaction.status}
                </Badge>
              </div>

              {/* Review reason */}
              {transaction.review_reason && (
                <div className="rounded-[var(--radius-md)] p-3 text-sm"
                  style={{ background: "var(--highlight-bg)", color: "var(--highlight-fg)", borderLeft: "3px solid var(--highlight)" }}>
                  {transaction.review_reason}
                </div>
              )}

              {/* Reason trail */}
              {transaction.reasons.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-[var(--fg-muted)] uppercase tracking-wide mb-2">Decision trail</p>
                  <ul className="space-y-1.5">
                    {transaction.reasons.map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-[var(--fg-muted)]">
                        <ChevronRight size={12} className="mt-0.5 shrink-0 text-[var(--accent)]" />
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Confidence */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-[var(--fg-muted)]">Confidence</span>
                  <span className="font-medium text-[var(--fg)]">{formatConfidence(transaction.confidence)}</span>
                </div>
                <div className="h-1.5 rounded-full" style={{ background: "var(--rule-line)" }}>
                  <div className="h-full rounded-full transition-all"
                    style={{ width: `${transaction.confidence * 100}%`, background: transaction.confidence >= 0.75 ? "var(--accent)" : "var(--highlight)" }} />
                </div>
              </div>

              {/* Category */}
              <Select
                label="Category"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                options={[
                  { value: "", label: "Uncategorized" },
                  ...categories.map((c) => ({ value: c.id, label: c.name })),
                ]}
              />

              {/* Note */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-[var(--fg-muted)]">Note</label>
                <textarea
                  rows={2}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Add a note…"
                  className="w-full rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--fg)] placeholder:text-[var(--fg-faint)] focus:outline-none focus:border-[var(--accent)] resize-none"
                />
              </div>

              {/* Options */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input type="checkbox" checked={applyToSimilar} onChange={(e) => setApplyToSimilar(e.target.checked)} className="accent-[var(--accent)]" />
                  <span className="text-[var(--fg-muted)]">Apply to similar transactions</span>
                </label>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input type="checkbox" checked={createRule} onChange={(e) => setCreateRule(e.target.checked)} className="accent-[var(--accent)]" />
                  <span className="text-[var(--fg-muted)]">Remember rule for &quot;{transaction.merchant}&quot;</span>
                </label>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t flex gap-3" style={{ borderColor: "var(--border)" }}>
              {transaction.status === "confirmed" && (
                <Button variant="outline" size="sm" onClick={() => undoMutation.mutate()} disabled={undoMutation.isPending}>
                  <RotateCcw size={14} />
                  Undo
                </Button>
              )}
              <Button className="flex-1" onClick={handleSave} disabled={patchMutation.isPending}>
                {patchMutation.isPending ? "Saving…" : "Confirm"}
              </Button>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
