"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type { Statement } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function StatementsPage() {
  const router = useRouter();
  const { data: statements, isLoading } = useQuery({
    queryKey: qk.statements(),
    queryFn: () => api.get("/statements") as Promise<Statement[]>,
  });

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold" style={{ fontFamily: "var(--font-display)", color: "var(--fg)" }}>
          Statements
        </h1>
        <Button size="sm" onClick={() => router.push("/upload")}>Upload new</Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-16" />)}
        </div>
      ) : !statements?.length ? (
        <Card>
          <CardContent className="py-16 text-center">
            <FileText size={40} className="mx-auto mb-4" style={{ color: "var(--fg-faint)" }} />
            <p className="text-[var(--fg-muted)] mb-4">No statements yet</p>
            <Button onClick={() => router.push("/upload")}>Upload your first statement</Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead style={{ background: "var(--surface-2)" }}>
                <tr>
                  <th className="px-4 py-3 text-left text-[var(--fg-muted)] font-medium">Filename</th>
                  <th className="px-4 py-3 text-left text-[var(--fg-muted)] font-medium">Period</th>
                  <th className="px-4 py-3 text-right text-[var(--fg-muted)] font-medium">Rows</th>
                  <th className="px-4 py-3 text-left text-[var(--fg-muted)] font-medium">Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {statements.map((s) => (
                  <tr
                    key={s.id}
                    className="border-t cursor-pointer hover:bg-[var(--surface-2)] transition-colors"
                    style={{ borderColor: "var(--rule-line)" }}
                    onClick={() => router.push(`/statements/${s.id}`)}
                  >
                    <td className="px-4 py-3 text-[var(--fg)] flex items-center gap-2">
                      <FileText size={14} style={{ color: "var(--fg-faint)" }} />
                      {s.filename}
                    </td>
                    <td className="px-4 py-3 text-[var(--fg-muted)]">
                      {s.period_start && s.period_end
                        ? `${formatDate(s.period_start)} to ${formatDate(s.period_end)}`
                        : "-"}
                    </td>
                    <td className="px-4 py-3 text-right text-[var(--fg)] tabular">{s.row_count}</td>
                    <td className="px-4 py-3 text-[var(--fg-muted)]">{formatDate(s.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
