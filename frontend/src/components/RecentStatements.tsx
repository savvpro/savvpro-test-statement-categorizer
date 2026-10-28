"use client";
import Link from "next/link";
import { useStatements } from "@/lib/api/hooks";
import { period } from "@/lib/format";

export function RecentStatements() {
  const { data, isLoading, isError } = useStatements();
  if (isLoading) return <p className="text-muted">Loading recent statements...</p>;
  if (isError) return null;
  if (!data || data.length === 0)
    return <p className="text-muted">Nothing uploaded yet. Your statements will appear here.</p>;
  return (
    <ul className="border-t border-rule">
      {data.map((s) => (
        <li key={s.id} className="border-b border-rule">
          <Link
            href={`/statements/${s.id}`}
            className="grid grid-cols-[1fr_auto] gap-x-6 gap-y-0 py-2 hover:bg-row sm:grid-cols-[minmax(0,2fr)_1fr_auto_auto]"
          >
            <span className="truncate font-medium">{s.filename}</span>
            <span className="text-muted">{period(s.period_start, s.period_end)}</span>
            <span className="num text-muted">{s.row_count} rows</span>
            <span className={s.counts.needs_review > 0 ? "text-attention" : "text-ledger"}>
              {s.counts.needs_review > 0 ? `${s.counts.needs_review} need review` : "All reviewed"}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
