"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type { Category, DashboardData } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Amount } from "@/components/ui/amount";

const GROUP_LABELS: Record<string, string> = {
  income: "Income",
  expense: "Business Expense",
  non_pl: "Non-P&L (Excluded from Schedule C)",
};

export default function CategoriesPage() {
  const router = useRouter();

  const { data: categories = [], isLoading: catsLoading } = useQuery({
    queryKey: qk.categories(),
    queryFn: () => api.get("/categories") as Promise<Category[]>,
  });

  const { data: dashData } = useQuery({
    queryKey: qk.dashboard(),
    queryFn: () => api.get("/dashboard") as Promise<DashboardData>,
  });

  const totalsByCat = Object.fromEntries(
    (dashData?.category_breakdown ?? []).map((b) => [b.slug, b.total_cents])
  );

  const groups = ["income", "expense", "non_pl"] as const;

  if (catsLoading) {
    return (
      <div className="p-6 max-w-4xl mx-auto space-y-4">
        {Array(3).fill(0).map((_, i) => <Skeleton key={i} className="h-48" />)}
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold" style={{ fontFamily: "var(--font-display)" }}>Categories</h1>
        <p className="text-sm text-[var(--fg-muted)]">Schedule C taxonomy. Click any category to see its transactions.</p>
      </div>

      {groups.map((group) => {
        const cats = categories.filter((c) => c.group === group);
        if (cats.length === 0) return null;
        return (
          <Card key={group}>
            <CardHeader>
              <CardTitle>{GROUP_LABELS[group]}</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-2)" }}>
                    <th className="px-4 py-3 text-left font-medium text-[var(--fg-muted)]">Category</th>
                    <th className="px-4 py-3 text-left font-medium text-[var(--fg-muted)] hidden md:table-cell">Sch C Line</th>
                    <th className="px-4 py-3 text-left font-medium text-[var(--fg-muted)] hidden md:table-cell">Deductible</th>
                    <th className="px-4 py-3 text-right font-medium text-[var(--fg-muted)]">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {cats.map((cat) => {
                    const total = totalsByCat[cat.id];
                    return (
                      <tr
                        key={cat.id}
                        onClick={() => router.push(`/transactions?category_id=${cat.id}`)}
                        className="cursor-pointer hover:bg-[var(--surface-2)] transition-colors"
                        style={{ borderBottom: "1px solid var(--rule-line)" }}
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            {cat.color && (
                              <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: cat.color }} />
                            )}
                            <div>
                              <div className="font-medium">{cat.name}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 hidden md:table-cell text-[var(--fg-muted)]">
                          {cat.schedule_c_line ?? "-"}
                        </td>
                        <td className="px-4 py-3 hidden md:table-cell text-[var(--fg-muted)]">
                          {cat.deductible_pct != null ? `${cat.deductible_pct}%` : "-"}
                        </td>
                        <td className="px-4 py-3 text-right tabular font-medium">
                          {total != null ? (
                            <Amount cents={total} />
                          ) : (
                            <span className="text-[var(--fg-faint)]">-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
