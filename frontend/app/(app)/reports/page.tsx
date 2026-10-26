"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Download, Printer } from "lucide-react";
import { api } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type { ReportSummary } from "@/lib/types";
import { formatCents } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Amount } from "@/components/ui/amount";

export default function ReportsPage() {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);

  const { data, isLoading } = useQuery({
    queryKey: qk.reports(year),
    queryFn: () => api.get("/reports/summary", { year }) as Promise<ReportSummary>,
  });

  function handleExport() {
    window.open(`/api/v1/reports/schedule-c.csv?year=${year}`, "_blank");
  }

  const lines = data?.schedule_c_lines ?? [];
  const incomeRows = lines.flatMap((l) =>
    l.categories.filter((c) => c.group === "income").map((c) => ({ ...c, line: l.line }))
  );
  const expenseRows = lines.flatMap((l) =>
    l.categories.filter((c) => c.group === "expense").map((c) => ({ ...c, line: l.line }))
  );
  const lineOrder = (l: string) => {
    const m = /^L?(\d+)([a-z]?)/i.exec(l);
    return m ? parseInt(m[1]) * 10 + (m[2] ? m[2].toLowerCase().charCodeAt(0) - 96 : 0) : 9999;
  };
  expenseRows.sort((a, b) => lineOrder(a.line) - lineOrder(b.line));
  const incomeTotal = incomeRows.reduce((s, c) => s + c.total_cents, 0);
  const expenseDeductible = expenseRows.reduce((s, c) => s + c.deductible_cents, 0);
  const netProfit = incomeTotal - expenseDeductible;
  const hasData = incomeRows.length > 0 || expenseRows.length > 0;

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between print:hidden">
        <div>
          <h1 className="text-2xl font-bold" style={{ fontFamily: "var(--font-display)" }}>Schedule C Report</h1>
          <p className="text-sm text-[var(--fg-muted)]">Profit or Loss from Business (Sole Proprietorship)</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={year}
            onChange={(e) => setYear(parseInt(e.target.value))}
            className="rounded-[var(--radius-md)] border px-3 py-2 text-sm"
            style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--fg)" }}
          >
            {[currentYear, currentYear - 1, currentYear - 2].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download size={14} /> CSV
          </Button>
          <Button variant="outline" size="sm" onClick={() => window.print()}>
            <Printer size={14} /> Print
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array(6).fill(0).map((_, i) => <Skeleton key={i} className="h-12" />)}
        </div>
      ) : !hasData ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-[var(--fg-muted)]">
            No data for {year}. Upload statements first.
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Income section */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
            <Card>
              <CardHeader>
                <CardTitle className="uppercase tracking-wide text-xs text-[var(--fg-muted)]">
                  Part I: Income
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <tbody>
                    {incomeRows.map((c) => (
                      <tr key={c.slug} style={{ borderBottom: "1px solid var(--rule-line)" }}>
                        <td className="px-4 py-3 text-[var(--fg-faint)] font-mono text-xs w-14">{c.line}</td>
                        <td className="px-4 py-3 text-[var(--fg-muted)]">{c.name}</td>
                        <td className="px-4 py-3 text-right tabular font-medium">
                          <Amount cents={c.total_cents} />
                        </td>
                      </tr>
                    ))}
                    <tr className="font-semibold" style={{ background: "var(--surface-2)", borderTop: "2px solid var(--border)" }}>
                      <td className="px-4 py-3 text-[var(--fg-faint)] font-mono text-xs">7</td>
                      <td className="px-4 py-3">Gross income</td>
                      <td className="px-4 py-3 text-right tabular" style={{ color: "var(--accent)" }}>
                        {formatCents(incomeTotal)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </CardContent>
            </Card>
          </motion.div>

          {/* Expenses section */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.08 }}>
            <Card>
              <CardHeader>
                <CardTitle className="uppercase tracking-wide text-xs text-[var(--fg-muted)]">
                  Part II: Expenses
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-2)" }}>
                      <th className="px-4 py-3 w-14 text-left text-[var(--fg-muted)] font-medium">Line</th>
                      <th className="px-4 py-3 text-left text-[var(--fg-muted)] font-medium">Expense</th>
                      <th className="px-4 py-3 text-right text-[var(--fg-muted)] font-medium">Total</th>
                      <th className="px-4 py-3 text-right text-[var(--fg-muted)] font-medium hidden md:table-cell">Deductible</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expenseRows.map((c) => (
                      <tr key={c.slug} style={{ borderBottom: "1px solid var(--rule-line)" }}>
                        <td className="px-4 py-3 text-[var(--fg-faint)] font-mono text-xs">{c.line}</td>
                        <td className="px-4 py-3 text-[var(--fg-muted)]">{c.name}</td>
                        <td className="px-4 py-3 text-right tabular">
                          {formatCents(c.total_cents, { absolute: true })}
                        </td>
                        <td className="px-4 py-3 text-right tabular hidden md:table-cell text-[var(--fg-muted)]">
                          {formatCents(c.deductible_cents, { absolute: true })}
                        </td>
                      </tr>
                    ))}
                    <tr className="font-semibold" style={{ background: "var(--surface-2)", borderTop: "2px solid var(--border)" }}>
                      <td className="px-4 py-3 text-[var(--fg-faint)] font-mono text-xs">28</td>
                      <td className="px-4 py-3">Total deductible expenses</td>
                      <td className="px-4 py-3" />
                      <td className="px-4 py-3 text-right tabular hidden md:table-cell" style={{ color: "var(--red-ink)" }}>
                        {formatCents(expenseDeductible, { absolute: true })}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </CardContent>
            </Card>
          </motion.div>

          {/* Net profit */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.16 }}>
            <Card style={{ borderColor: netProfit >= 0 ? "var(--accent)" : "var(--red-ink)" }}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-[var(--fg-muted)] uppercase tracking-wide">Line 31: Net profit or (loss)</div>
                    <div className="text-3xl font-bold tabular mt-1" style={{ fontFamily: "var(--font-display)" }}>
                      <Amount cents={netProfit} />
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-[var(--fg-muted)]">Tax year</div>
                    <div className="text-2xl font-bold" style={{ fontFamily: "var(--font-display)", color: "var(--fg-muted)" }}>
                      {year}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Non-P&L excluded */}
          {data && data.non_pl_summary && data.non_pl_summary.count > 0 && (
            <p className="text-xs text-[var(--fg-faint)] px-1">
              {data.non_pl_summary.count} non-P&L movement{data.non_pl_summary.count !== 1 ? "s" : ""} (transfers,
              card payments, owner draws, tax payments) totaling {formatCents(data.non_pl_summary.total_cents, { absolute: true })} are
              tracked separately and excluded from Schedule C totals.
            </p>
          )}
        </>
      )}
    </div>
  );
}
