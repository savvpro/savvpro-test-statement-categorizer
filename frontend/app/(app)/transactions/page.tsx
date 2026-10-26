"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Search, X, Download } from "lucide-react";
import { api } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type { Transaction, Category, PaginatedTransactions } from "@/lib/types";
import { formatDate, formatConfidence } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Amount } from "@/components/ui/amount";
import { toast } from "sonner";

type Filters = {
  status: string;
  search: string;
  category_id: string;
  page: number;
};

const PAGE_SIZE = 25;

function TransactionDrawer({
  txn,
  categories,
  onClose,
}: {
  txn: Transaction;
  categories: Category[];
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [newCat, setNewCat] = useState(txn.category_id ?? "");
  const [note, setNote] = useState(txn.note ?? "");
  const [applySimilar, setApplySimilar] = useState(false);
  const [createRule, setCreateRule] = useState(false);

  const patch = useMutation({
    mutationFn: () =>
      api.patch(`/transactions/${txn.id}`, {
        category_id: newCat || null,
        status: "confirmed",
        note,
        apply_to_similar: applySimilar && !!newCat,
        create_rule: createRule && !!newCat,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.transactions() });
      qc.invalidateQueries({ queryKey: qk.dashboard() });
      qc.invalidateQueries({ queryKey: qk.reviewQueue() });
      qc.invalidateQueries({ queryKey: qk.rules() });
      toast.success("Transaction updated");
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <motion.div
      initial={{ x: "100%" }}
      animate={{ x: 0 }}
      exit={{ x: "100%" }}
      transition={{ type: "spring", damping: 30, stiffness: 320 }}
      className="fixed right-0 top-0 bottom-0 w-full max-w-sm z-50 flex flex-col"
      style={{ background: "var(--surface)", borderLeft: "1px solid var(--border)", boxShadow: "var(--shadow-lg)" }}
    >
      <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: "var(--border)" }}>
        <h2 className="font-semibold text-sm" style={{ fontFamily: "var(--font-display)" }}>Transaction Detail</h2>
        <button onClick={onClose} className="p-1 rounded hover:bg-[var(--surface-2)] transition-colors"><X size={16} /></button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div>
          <div className="text-xs text-[var(--fg-muted)]">{formatDate(txn.posted_date)}</div>
          <div className="font-medium mt-1">{txn.merchant || txn.description_raw}</div>
          <div className="text-2xl font-bold mt-1 tabular" style={{ fontFamily: "var(--font-display)" }}>
            <Amount cents={txn.amount_cents} />
          </div>
        </div>

        {txn.review_reason && (
          <div className="rounded-[var(--radius-md)] p-3 text-sm" style={{ background: "var(--highlight-bg)", color: "var(--highlight-fg)", borderLeft: "3px solid var(--highlight)" }}>
            {txn.review_reason}
          </div>
        )}

        <div>
          <label className="text-xs font-medium text-[var(--fg-muted)] block mb-1">Category</label>
          <select
            value={newCat}
            onChange={(e) => setNewCat(e.target.value)}
            className="w-full rounded-[var(--radius-md)] border px-3 py-2 text-sm"
            style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--fg)" }}
          >
            <option value="">Uncategorized</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs font-medium text-[var(--fg-muted)] block mb-1">Note</label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            placeholder="Add a note"
            className="w-full rounded-[var(--radius-md)] border px-3 py-2 text-sm resize-none"
            style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--fg)" }}
          />
        </div>

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={applySimilar} onChange={(e) => setApplySimilar(e.target.checked)} className="accent-[var(--accent)]" />
            <span className="text-[var(--fg-muted)]">Apply to other unconfirmed rows from {txn.merchant || "this merchant"}</span>
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={createRule} onChange={(e) => setCreateRule(e.target.checked)} className="accent-[var(--accent)]" />
            <span className="text-[var(--fg-muted)]">Always categorize {txn.merchant || "this merchant"} this way (create rule)</span>
          </label>
        </div>

        {txn.reasons && txn.reasons.length > 0 && (
          <div>
            <div className="text-xs font-medium text-[var(--fg-muted)] mb-2">Reason trail</div>
            <ol className="space-y-1">
              {txn.reasons.map((r, i) => (
                <li key={i} className="text-xs flex gap-2">
                  <span className="text-[var(--fg-faint)] shrink-0">{i + 1}.</span>
                  <span className="text-[var(--fg-muted)]">{r}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        <div className="flex items-center gap-2 text-xs text-[var(--fg-muted)]">
          <span>Confidence:</span>
          <div className="flex-1 h-1.5 rounded-full" style={{ background: "var(--border)" }}>
            <motion.div
              className="h-full rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${(txn.confidence ?? 0) * 100}%` }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              style={{ background: (txn.confidence ?? 0) >= 0.75 ? "var(--accent)" : "var(--highlight)" }}
            />
          </div>
          <span>{formatConfidence(txn.confidence ?? 0)}</span>
        </div>
      </div>

      <div className="p-4 border-t flex gap-2" style={{ borderColor: "var(--border)" }}>
        <Button onClick={() => patch.mutate()} disabled={patch.isPending} className="flex-1">
          {patch.isPending ? "Saving" : "Confirm & Save"}
        </Button>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
      </div>
    </motion.div>
  );
}

function TransactionsInner() {
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<Filters>({
    status: "",
    search: "",
    category_id: searchParams.get("category_id") ?? "",
    page: 1,
  });
  const [selected, setSelected] = useState<Transaction | null>(null);

  const { data: categoriesData } = useQuery({
    queryKey: qk.categories(),
    queryFn: () => api.get("/categories") as Promise<Category[]>,
  });
  const categories = categoriesData ?? [];
  const catName = (id: string | null) => (id ? categories.find((c) => c.id === id)?.name ?? id : "-");

  const { data, isLoading } = useQuery({
    queryKey: qk.transactions(filters),
    queryFn: () =>
      api.get("/transactions", {
        status: filters.status || undefined,
        search: filters.search || undefined,
        category_id: filters.category_id || undefined,
        page: filters.page,
        page_size: PAGE_SIZE,
      }) as Promise<PaginatedTransactions>,
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / (data.page_size || PAGE_SIZE))) : 1;

  function handleExport() {
    window.open("/api/v1/transactions/export.csv", "_blank");
  }

  const statusBadge = (s: string) => {
    if (s === "needs_review") return <Badge variant="review">Needs Review</Badge>;
    if (s === "confirmed") return <Badge variant="confirmed">Confirmed</Badge>;
    return <Badge variant="auto">Auto</Badge>;
  };

  const hasFilters = filters.search || filters.status || filters.category_id;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold" style={{ fontFamily: "var(--font-display)" }}>Transactions</h1>
        <Button variant="outline" size="sm" onClick={handleExport}>
          <Download size={14} /> Export CSV
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-48">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--fg-faint)]" />
              <Input
                placeholder="Search merchant"
                value={filters.search}
                onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value, page: 1 }))}
                className="pl-8"
              />
            </div>
            <select
              value={filters.status}
              onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value, page: 1 }))}
              className="rounded-[var(--radius-md)] border px-3 py-2 text-sm"
              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--fg)" }}
            >
              <option value="">All statuses</option>
              <option value="auto">Auto</option>
              <option value="needs_review">Needs Review</option>
              <option value="confirmed">Confirmed</option>
            </select>
            <select
              value={filters.category_id}
              onChange={(e) => setFilters((f) => ({ ...f, category_id: e.target.value, page: 1 }))}
              className="rounded-[var(--radius-md)] border px-3 py-2 text-sm"
              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--fg)" }}
            >
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            {hasFilters && (
              <Button variant="ghost" size="sm" onClick={() => setFilters({ status: "", search: "", category_id: "", page: 1 })}>
                <X size={14} /> Clear
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <div className="rounded-[var(--radius-lg)] border overflow-hidden" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
        <table className="w-full text-sm ledger-lines">
          <thead>
            <tr className="text-left" style={{ background: "var(--surface-2)", borderBottom: "2px solid var(--border)" }}>
              <th className="px-4 py-3 font-medium text-[var(--fg-muted)]">Date</th>
              <th className="px-4 py-3 font-medium text-[var(--fg-muted)]">Merchant</th>
              <th className="px-4 py-3 font-medium text-[var(--fg-muted)] text-right">Amount</th>
              <th className="px-4 py-3 font-medium text-[var(--fg-muted)] hidden md:table-cell">Category</th>
              <th className="px-4 py-3 font-medium text-[var(--fg-muted)] hidden md:table-cell">Status</th>
              <th className="px-4 py-3 font-medium text-[var(--fg-muted)] hidden lg:table-cell text-right">Conf.</th>
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array(8).fill(0).map((_, i) => (
                  <tr key={i}>
                    {Array(6).fill(0).map((_, j) => (
                      <td key={j} className="px-4 py-3"><Skeleton className="h-4" /></td>
                    ))}
                  </tr>
                ))
              : data?.items.map((tx) => (
                  <tr
                    key={tx.id}
                    onClick={() => setSelected(tx)}
                    className="cursor-pointer transition-colors hover:bg-[var(--surface-2)]"
                    style={tx.status === "needs_review" ? { borderLeft: "3px solid var(--highlight)" } : { borderLeft: "3px solid transparent" }}
                  >
                    <td className="px-4 py-3 text-[var(--fg-muted)] whitespace-nowrap">{formatDate(tx.posted_date)}</td>
                    <td className="px-4 py-3 font-medium max-w-xs truncate">{tx.merchant || tx.description_raw}</td>
                    <td className="px-4 py-3 text-right tabular font-medium">
                      <Amount cents={tx.amount_cents} />
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell text-[var(--fg-muted)]">
                      {catName(tx.category_id)}
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">{statusBadge(tx.status)}</td>
                    <td className="px-4 py-3 hidden lg:table-cell text-right text-[var(--fg-muted)]">
                      {tx.confidence != null ? formatConfidence(tx.confidence) : "-"}
                    </td>
                  </tr>
                ))
            }
          </tbody>
        </table>

        {data && data.items.length === 0 && (
          <div className="py-16 text-center text-[var(--fg-muted)] text-sm">No transactions found</div>
        )}
      </div>

      {/* Pagination */}
      {data && totalPages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--fg-muted)]">
            Page {data.page} of {totalPages} ({data.total} transactions)
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={data.page <= 1}
              onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}>
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={data.page >= totalPages}
              onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}>
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Drawer */}
      <AnimatePresence>
        {selected && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/30"
              onClick={() => setSelected(null)}
            />
            <TransactionDrawer
              txn={selected}
              categories={categories}
              onClose={() => setSelected(null)}
            />
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function TransactionsPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-[var(--fg-muted)]">Loading transactions…</div>}>
      <TransactionsInner />
    </Suspense>
  );
}
