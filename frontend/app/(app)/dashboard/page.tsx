"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { useEffect } from "react";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
} from "recharts";
import { api } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type { DashboardData } from "@/lib/types";
import { formatCents, formatDate } from "@/lib/format";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, TrendingUp, TrendingDown, DollarSign, FileText, ArrowRight } from "lucide-react";

function CountUp({ value, prefix = "" }: { value: number; prefix?: string }) {
  const count = useMotionValue(0);
  const display = useTransform(count, (v) => {
    const dollars = Math.abs(v) / 100;
    const f = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(dollars);
    return `${v < 0 ? "-" : ""}${prefix}${f}`;
  });

  useEffect(() => {
    const ctrl = animate(count, value, { duration: 1.1, ease: [0.2, 0.8, 0.2, 1] });
    return ctrl.stop;
  }, [value, count]);

  return <motion.span>{display}</motion.span>;
}

const easeOut = [0.2, 0.8, 0.2, 1] as const;

export default function DashboardPage() {
  const router = useRouter();
  const { data, isLoading } = useQuery({
    queryKey: qk.dashboard(),
    queryFn: () => api.get("/dashboard") as Promise<DashboardData>,
  });

  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-4 max-w-7xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-32" />)}
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          <Skeleton className="h-72" />
          <Skeleton className="h-72" />
        </div>
      </div>
    );
  }

  const kpis = [
    { label: "Income", value: data.income_cents, icon: TrendingUp, color: "var(--accent)", bg: "var(--accent-light)" },
    { label: "Deductible Expenses", value: data.deductible_expenses_cents, icon: TrendingDown, color: "var(--red-ink)", bg: "var(--red-bg)" },
    { label: "Est. Net Profit", value: data.net_profit_cents, icon: DollarSign, color: "var(--fg)", bg: "var(--surface-2)" },
    { label: "Needs Review", value: data.needs_review_count, icon: AlertCircle, color: "var(--highlight-fg)", bg: "var(--highlight-bg)", isCount: true },
  ];

  const breakdown = (data.category_breakdown ?? []).filter((c) => c.group === "expense");
  const expenseSlice = breakdown.slice(0, 8);
  const monthly = (data.monthly_trend ?? []).map((m) => ({
    month: m.month.slice(5),
    Income: m.income,
    Expenses: m.expenses,
  }));
  const recent = data.recent_imports ?? [];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: easeOut }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold" style={{ fontFamily: "var(--font-display)", color: "var(--fg)" }}>
            Dashboard
          </h1>
          <p className="text-sm text-[var(--fg-muted)]">Your Schedule C overview for the current year</p>
        </div>
        {data.needs_review_count > 0 && (
          <Button onClick={() => router.push("/review")}>
            <AlertCircle size={15} />
            Clear {data.needs_review_count} in queue
          </Button>
        )}
      </motion.div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map(({ label, value, icon: Icon, color, bg, isCount }, i) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07, duration: 0.45, ease: easeOut }}
          >
            <Card className="lift h-full">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between mb-3">
                  <div className="w-9 h-9 rounded-[var(--radius-md)] flex items-center justify-center"
                    style={{ background: bg }}>
                    <Icon size={18} style={{ color }} />
                  </div>
                </div>
                <div className="text-2xl font-bold tabular" style={{ color, fontFamily: "var(--font-display)" }}>
                  {isCount ? (
                    <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>
                      {value}
                    </motion.span>
                  ) : (
                    <CountUp value={value as number} />
                  )}
                </div>
                <p className="text-xs text-[var(--fg-muted)] mt-1">{label}</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Donut chart */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25, duration: 0.45, ease: easeOut }}>
          <Card className="h-full">
            <CardHeader><CardTitle>Expense Breakdown</CardTitle></CardHeader>
            <CardContent>
              {expenseSlice.length === 0 ? (
                <p className="text-sm text-[var(--fg-muted)] py-8 text-center">No expense data yet</p>
              ) : (
                <div className="flex flex-col sm:flex-row gap-4 items-center">
                  <ResponsiveContainer width={160} height={160}>
                    <PieChart>
                      <Pie data={expenseSlice} dataKey={(d) => Math.abs(d.total_cents)} innerRadius={50} outerRadius={75} paddingAngle={2} animationDuration={700}>
                        {expenseSlice.map((entry) => (
                          <Cell key={entry.slug} fill={entry.color || "var(--accent)"} stroke="var(--surface)" strokeWidth={2} />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(v) => formatCents(Number(v), { absolute: true })}
                        contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12, color: "var(--fg)" }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex-1 min-w-0 w-full space-y-2">
                    {expenseSlice.map((c) => (
                      <div key={c.slug} className="flex items-center gap-2 text-xs">
                        <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: c.color }} />
                        <span className="flex-1 truncate text-[var(--fg-muted)]">{c.name}</span>
                        <span className="font-medium tabular text-[var(--fg)]">{formatCents(c.total_cents, { absolute: true })}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Monthly bar chart */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.32, duration: 0.45, ease: easeOut }}>
          <Card className="h-full">
            <CardHeader><CardTitle>Monthly Income vs Expenses</CardTitle></CardHeader>
            <CardContent>
              {monthly.length === 0 ? (
                <p className="text-sm text-[var(--fg-muted)] py-8 text-center">No monthly data yet</p>
              ) : (
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={monthly} barSize={14}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--rule-line)" vertical={false} />
                    <XAxis dataKey="month" tick={{ fontSize: 11, fill: "var(--fg-muted)" }} axisLine={{ stroke: "var(--border)" }} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "var(--fg-muted)" }} tickFormatter={(v) => `$${Math.abs(v / 100).toFixed(0)}`} axisLine={false} tickLine={false} width={44} />
                    <Tooltip
                      cursor={{ fill: "color-mix(in srgb, var(--fg) 5%, transparent)" }}
                      formatter={(v) => formatCents(Number(v), { absolute: true })}
                      contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12, color: "var(--fg)" }}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="Income" fill="var(--accent)" radius={[3, 3, 0, 0]} animationDuration={700} />
                    <Bar dataKey="Expenses" fill="var(--red-ink)" radius={[3, 3, 0, 0]} animationDuration={700} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Recent imports */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4, duration: 0.45, ease: easeOut }}>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Imports</CardTitle>
            <button
              onClick={() => router.push("/statements")}
              className="text-xs text-[var(--accent)] link-underline inline-flex items-center gap-1"
            >
              View all <ArrowRight size={12} />
            </button>
          </CardHeader>
          <CardContent className="p-0">
            {recent.length === 0 ? (
              <div className="py-10 text-center text-sm text-[var(--fg-muted)]">
                No statements imported yet.{" "}
                <button onClick={() => router.push("/upload")} className="text-[var(--accent)] link-underline">Upload one</button>
              </div>
            ) : (
              <ul>
                {recent.map((imp) => (
                  <li
                    key={imp.id}
                    onClick={() => router.push(`/statements/${imp.id}`)}
                    className="flex items-center gap-3 px-6 py-3 cursor-pointer hover:bg-[var(--surface-2)] transition-colors"
                    style={{ borderTop: "1px solid var(--rule-line)" }}
                  >
                    <FileText size={15} style={{ color: "var(--fg-faint)" }} />
                    <span className="flex-1 text-sm text-[var(--fg)] truncate">{imp.filename}</span>
                    <span className="text-xs tabular text-[var(--fg-muted)]">{imp.row_count} rows</span>
                    <span className="text-xs text-[var(--fg-faint)] hidden sm:block">{formatDate(imp.created_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
