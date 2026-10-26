"use client";

import { Info, Loader2, TriangleAlert } from "lucide-react";
import type { Transaction } from "@/lib/api";
import { formatDate, formatPercent, formatSignedMoney } from "@/lib/format";
import { StatusPill, cx } from "./ui";

function ConfidenceCell({ value }: { value: number }) {
  const pct = Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0;
  const bar = pct >= 0.85 ? "bg-accent" : pct >= 0.5 ? "bg-amber-line" : "bg-red/60";
  return (
    <div className="flex items-center justify-end gap-2">
      <span className="w-10 text-right text-sm tabular-nums text-ink">{formatPercent(pct)}</span>
      <span className="h-1.5 w-12 overflow-hidden rounded-full bg-grey-soft" aria-hidden="true">
        <span className={cx("block h-full rounded-full", bar)} style={{ width: `${pct * 100}%` }} />
      </span>
    </div>
  );
}

export function TransactionTable({
  rows,
  categories,
  savingId,
  onCategoryChange,
}: {
  rows: Transaction[];
  categories: string[];
  savingId: number | null;
  onCategoryChange: (tx: Transaction, category: string) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[1000px] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-line text-[11px] font-semibold uppercase tracking-wider text-faint">
            <th scope="col" className="w-[120px] py-3 pl-5 pr-3 font-semibold">
              Date
            </th>
            <th scope="col" className="py-3 pr-4 font-semibold">
              Merchant
            </th>
            <th scope="col" className="w-[250px] py-3 pr-4 font-semibold">
              Category
            </th>
            <th scope="col" className="w-[130px] py-3 pr-4 text-right font-semibold">
              Amount
            </th>
            <th scope="col" className="w-[120px] py-3 pr-4 text-right font-semibold">
              Confidence
            </th>
            <th scope="col" className="w-[130px] py-3 pr-5 font-semibold">
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((tx) => {
            const flagged = tx.status === "needs_review" || tx.status === "duplicate";
            const saving = savingId === tx.id;
            const options = categories.includes(tx.category) ? categories : [tx.category, ...categories];
            return (
              <tr key={tx.id} className="border-b border-line align-top last:border-b-0 hover:bg-page/70">
                <td
                  className={cx(
                    "py-3.5 pl-5 pr-3 whitespace-nowrap tabular-nums text-muted",
                    flagged && "shadow-[inset_3px_0_0_var(--color-amber-line)]",
                  )}
                >
                  {formatDate(tx.date)}
                </td>
                <td className="py-3.5 pr-4">
                  <p className="font-semibold text-ink">
                    {tx.normalized_merchant || tx.description || "Unknown merchant"}
                  </p>
                  <p className="mt-0.5 break-all text-xs text-faint">{tx.description}</p>
                  {tx.reason ? (
                    <p className="mt-1.5 flex items-start gap-1.5 text-xs text-muted">
                      <Info size={13} strokeWidth={1.75} className="mt-px shrink-0 text-faint" aria-hidden="true" />
                      <span>
                        <span className="sr-only">Why: </span>
                        {tx.reason}
                      </span>
                    </p>
                  ) : null}
                  {tx.notes?.map((note) => (
                    <p key={note} className="mt-1 flex items-start gap-1.5 text-xs text-amber">
                      <TriangleAlert size={13} strokeWidth={1.75} className="mt-px shrink-0" aria-hidden="true" />
                      <span>{note}</span>
                    </p>
                  ))}
                </td>
                <td className="py-3 pr-4">
                  <div className="relative">
                    <select
                      aria-label={`Category for ${tx.normalized_merchant || tx.description}`}
                      value={tx.category}
                      disabled={saving}
                      onChange={(e) => onCategoryChange(tx, e.target.value)}
                      className={cx(
                        "h-9 w-full rounded-lg border bg-card pl-2.5 pr-8 text-sm text-ink transition-colors hover:border-line-strong focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/15 disabled:opacity-60",
                        tx.category === "Needs Review" ? "border-amber-line/60" : "border-line",
                      )}
                    >
                      {options.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                    {saving ? (
                      <Loader2
                        size={14}
                        className="pointer-events-none absolute right-7 top-1/2 -translate-y-1/2 animate-spin text-accent"
                        aria-label="Saving"
                      />
                    ) : null}
                  </div>
                </td>
                <td
                  className={cx(
                    "py-3.5 pr-4 text-right whitespace-nowrap font-medium tabular-nums",
                    tx.amount > 0 ? "text-green" : "text-ink",
                  )}
                >
                  {formatSignedMoney(tx.amount, tx.currency)}
                  {tx.currency && tx.currency.toUpperCase() !== "USD" ? (
                    <span className="block text-[11px] font-normal text-faint">{tx.currency.toUpperCase()}</span>
                  ) : null}
                </td>
                <td className="py-3.5 pr-4">
                  <ConfidenceCell value={tx.confidence} />
                </td>
                <td className="py-3.5 pr-5">
                  <StatusPill status={tx.status} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
