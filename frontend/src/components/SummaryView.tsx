"use client";
import Link from "next/link";
import { TopBar } from "./TopBar";
import { api } from "@/lib/api/client";
import { useCategories, useStatement, useSummary, useTransactions } from "@/lib/api/hooks";
import type { CategoryOut, StatementOut, SummaryOut, TransactionOut } from "@/lib/api/types";
import { money, period, plainAmount } from "@/lib/format";

interface Row {
  line: string;
  label: string;
  category: string;
  total: number;
  pending: number;
}

export function buildRows(summary: SummaryOut, cats: CategoryOut[], pendingTxs: TransactionOut[]): Row[] {
  const pending: Record<string, number> = {};
  for (const t of pendingTxs) {
    const c = t.category ?? t.brain_category;
    if (c) pending[c] = (pending[c] ?? 0) + Math.abs(t.amount_cents);
  }
  const totals = new Map(summary.schedule_e.map((l) => [l.category, l]));
  return cats
    .filter((c) => c.schedule_e_line && (totals.has(c.code) || pending[c.code]))
    .map((c) => ({
      line: c.schedule_e_line as string,
      label: totals.get(c.code)?.label ?? c.label,
      category: c.code,
      total: totals.get(c.code)?.total_cents ?? 0,
      pending: pending[c.code] ?? 0,
    }))
    .sort((a, b) => Number(a.line) - Number(b.line));
}

export function ScheduleEForm({
  statement,
  summary,
  categories,
  pendingTxs,
}: {
  statement: StatementOut | undefined;
  summary: SummaryOut;
  categories: CategoryOut[];
  pendingTxs: TransactionOut[];
}) {
  const rows = buildRows(summary, categories, pendingTxs);
  const expenseRows = rows.filter((r) => Number(r.line) > 3);
  const maxExpense = Math.max(1, ...expenseRows.map((r) => Math.abs(r.total)));
  const totalExpenses = Math.abs(summary.total_expense_cents);
  const excluded = Object.entries(summary.excluded).filter(([, v]) => v !== 0);
  const left = summary.unresolved.count;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h1 className="text-xl font-semibold">
          Schedule E, Part I{statement ? `, ${period(statement.period_start, statement.period_end)}` : ""}
        </h1>
        <a href={statement ? api.exportUrl(statement.id) : "#"} className="rounded-xs bg-ledger px-4 py-2 font-medium text-white" download>
          Export CSV
        </a>
      </div>

      {left > 0 ? (
        <p className="mt-3 border-l-4 border-attention bg-attention-fill px-3 py-2 text-attention">
          {left} {left === 1 ? "row still needs" : "rows still need"} review ({money(summary.unresolved.total_abs_cents)}).{" "}
          {statement && (
            <Link href={`/statements/${statement.id}`} className="font-medium underline">
              Resolve them
            </Link>
          )}
        </p>
      ) : (
        <p className="mt-3 text-ledger">All rows reviewed. Your Schedule E is ready to export.</p>
      )}

      <table className="mt-4 w-full border-collapse bg-row">
        <caption className="sr-only">Schedule E Part I lines</caption>
        <thead className="sr-only">
          <tr><th>Line</th><th>Description</th><th>Share of expenses</th><th>Amount</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const isIncome = Number(r.line) === 3;
            const share = Math.abs(r.total) / maxExpense;
            return (
              <Line key={r.category} n={r.line} label={r.label}>
                <td className="hidden w-32 sm:table-cell">
                  {!isIncome && r.total !== 0 && (
                    <svg viewBox="0 0 100 8" className="h-2 w-full" role="img" aria-label={`${Math.round((Math.abs(r.total) / (totalExpenses || 1)) * 100)}% of expenses`}>
                      <rect width="100" height="8" fill="var(--rule)" />
                      <rect width={Math.max(2, share * 100)} height="8" fill="var(--ledger)" />
                    </svg>
                  )}
                </td>
                <td className="num whitespace-nowrap py-2 pr-3">
                  {r.pending > 0 && (
                    <span className="mr-3 text-attention">pending {plainAmount(r.pending)}</span>
                  )}
                  {plainAmount(isIncome ? r.total : Math.abs(r.total))}
                </td>
              </Line>
            );
          })}
          <Line n="20" label="Total expenses">
            <td />
            <td className="num py-2 pr-3 font-medium">{plainAmount(totalExpenses)}</td>
          </Line>
          <Line n="21" label="Income or loss">
            <td />
            <td className="num py-2 pr-3 font-semibold">{plainAmount(summary.net_cents)}</td>
          </Line>
        </tbody>
      </table>

      <h2 className="mb-1 mt-8 font-semibold">Not counted on Schedule E</h2>
      {excluded.length === 0 ? (
        <p className="text-muted">Nothing was left out.</p>
      ) : (
        <ul className="divide-y divide-rule border-y border-rule bg-row">
          {excluded.map(([code, cents]) => (
            <li key={code} className="flex justify-between px-3 py-2 text-muted">
              <span>{categories.find((c) => c.code === code)?.label ?? code}</span>
              <span className="num">{plainAmount(Math.abs(cents))}</span>
            </li>
          ))}
        </ul>
      )}
      {summary.duplicates.count > 0 && (
        <p className="mt-3 text-muted">
          {summary.duplicates.count} duplicate {summary.duplicates.count === 1 ? "row was" : "rows were"} skipped.
        </p>
      )}
    </div>
  );
}

export function SummaryView({ id }: { id: string }) {
  const st = useStatement(id);
  const summary = useSummary(id);
  const cats = useCategories();
  const txs = useTransactions(id);
  const pendingTxs = (txs.data?.items ?? []).filter((t) => t.status === "needs_review");

  return (
    <>
      <TopBar step={3} statementId={id} title={st.data?.filename} />
      {summary.isError ? (
        <p role="alert" className="mx-auto max-w-3xl px-4 py-8 text-error">
          {summary.error.message}{" "}
          <button type="button" className="underline" onClick={() => void summary.refetch()}>Try again</button>
        </p>
      ) : summary.data && cats.data ? (
        <ScheduleEForm statement={st.data} summary={summary.data} categories={cats.data} pendingTxs={pendingTxs} />
      ) : (
        <p className="mx-auto max-w-3xl px-4 py-8 text-muted">Loading your Schedule E...</p>
      )}
    </>
  );
}


function Line({ n, label, children }: { n: string; label: string; children: React.ReactNode }) {
  return (
    <tr className="border-b border-rule">
      <th scope="row" className="w-12 py-2 pl-3 text-left font-normal text-muted">{n}</th>
      <td className="py-2">{label}</td>
      {children}
    </tr>
  );
}
