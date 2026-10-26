"use client";

import { use, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type { Statement, Transaction, Category } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { Amount } from "@/components/ui/amount";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronDown, ChevronRight, Trash2, ArrowLeft } from "lucide-react";
import { toast } from "sonner";

function SkipAccordion({ skipped }: { skipped: { line: number; reason: string }[] }) {
  const [open, setOpen] = useState(false);
  if (!skipped.length) return null;
  return (
    <Card>
      <button
        className="w-full px-6 py-4 flex items-center gap-2 text-sm text-[var(--fg-muted)] hover:text-[var(--fg)] transition-colors"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        {skipped.length} skipped row{skipped.length !== 1 ? "s" : ""}
      </button>
      {open && (
        <div className="border-t px-6 py-3 space-y-2" style={{ borderColor: "var(--border)" }}>
          {skipped.map((s) => (
            <div key={s.line} className="flex gap-3 text-xs text-[var(--fg-muted)]">
              <span className="font-medium text-[var(--fg)] w-12">Line {s.line}</span>
              <span>{s.reason}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default function StatementDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const qc = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: statement, isLoading: stmtLoading } = useQuery({
    queryKey: qk.statement(id),
    queryFn: () => api.get(`/statements/${id}`) as Promise<Statement>,
  });

  const { data: txData, isLoading: txLoading } = useQuery({
    queryKey: qk.transactions({ statement: id }),
    queryFn: () => api.get("/transactions", { statement_id: id, page_size: 200 }) as Promise<{ items: Transaction[]; total: number }>,
  });

  const { data: categories = [] } = useQuery({
    queryKey: qk.categories(),
    queryFn: () => api.get("/categories") as Promise<Category[]>,
  });
  const catName = (cid: string | null) => (cid ? categories.find((c) => c.id === cid)?.name ?? cid : "-");

  const deleteMutation = useMutation({
    mutationFn: () => api.del(`/statements/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.statements() });
      toast.success("Statement deleted");
      router.push("/statements");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (stmtLoading) return <div className="p-6 space-y-4"><Skeleton className="h-24" /><Skeleton className="h-72" /></div>;
  if (!statement) return <div className="p-6 text-[var(--fg-muted)]">Statement not found</div>;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => router.push("/statements")}>
          <ArrowLeft size={16} />
        </Button>
        <h1 className="text-xl font-bold" style={{ fontFamily: "var(--font-display)", color: "var(--fg)" }}>
          {statement.filename}
        </h1>
      </div>

      <Card>
        <CardContent className="pt-6 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div><p className="text-[var(--fg-muted)] text-xs">Period</p>
            <p className="font-medium text-[var(--fg)]">
              {statement.period_start ? `${formatDate(statement.period_start)} to ${formatDate(statement.period_end!)}` : "-"}
            </p>
          </div>
          <div><p className="text-[var(--fg-muted)] text-xs">Rows</p><p className="font-medium text-[var(--fg)]">{statement.row_count}</p></div>
          <div><p className="text-[var(--fg-muted)] text-xs">Uploaded</p><p className="font-medium text-[var(--fg)]">{formatDate(statement.created_at)}</p></div>
          <div className="flex items-end">
            <Button variant="outline" size="sm" onClick={() => setConfirmDelete(true)}>
              <Trash2 size={14} className="text-[var(--red-ink)]" />
              Delete
            </Button>
          </div>
        </CardContent>
      </Card>

      <SkipAccordion skipped={statement.skipped_rows} />

      <Card>
        <CardHeader><CardTitle>Transactions ({txData?.total ?? 0})</CardTitle></CardHeader>
        <div className="overflow-x-auto">
          {txLoading ? (
            <div className="p-4 space-y-3">{[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10" />)}</div>
          ) : (
            <table className="w-full text-sm">
              <thead style={{ background: "var(--surface-2)" }}>
                <tr>
                  <th className="px-4 py-3 text-left text-[var(--fg-muted)] font-medium">Date</th>
                  <th className="px-4 py-3 text-left text-[var(--fg-muted)] font-medium">Merchant</th>
                  <th className="px-4 py-3 text-right text-[var(--fg-muted)] font-medium">Amount</th>
                  <th className="px-4 py-3 text-left text-[var(--fg-muted)] font-medium">Category</th>
                  <th className="px-4 py-3 text-left text-[var(--fg-muted)] font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {txData?.items.map((t) => (
                  <tr key={t.id} className="border-t" style={{ borderColor: "var(--rule-line)" }}>
                    <td className="px-4 py-2.5 text-[var(--fg-muted)]">{formatDate(t.posted_date)}</td>
                    <td className="px-4 py-2.5 text-[var(--fg)]">{t.merchant}</td>
                    <td className="px-4 py-2.5 text-right"><Amount cents={t.amount_cents} /></td>
                    <td className="px-4 py-2.5 text-[var(--fg-muted)]">{catName(t.category_id)}</td>
                    <td className="px-4 py-2.5">
                      <Badge variant={t.status === "needs_review" ? "review" : t.status === "confirmed" ? "confirmed" : "auto"}>
                        {t.status === "needs_review" ? "Review" : t.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>

      <Dialog open={confirmDelete} onClose={() => setConfirmDelete(false)} title="Delete statement?">
        <p className="text-sm text-[var(--fg-muted)] mb-4">
          This will permanently delete the statement and all its transactions. This cannot be undone.
        </p>
        <div className="flex gap-3 justify-end">
          <Button variant="outline" onClick={() => setConfirmDelete(false)}>Cancel</Button>
          <Button variant="destructive" onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
            {deleteMutation.isPending ? "Deleting…" : "Delete"}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
