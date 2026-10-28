"use client";
import { useEffect, useRef } from "react";
import { amount, shortDate } from "@/lib/format";
import { categoryLabel, STATUS_LABEL } from "@/lib/categories";
import type { CategoryOut, TransactionOut } from "@/lib/api/types";

function StatusMark({ tx }: { tx: TransactionOut }) {
  const [shape, cls] =
    tx.status === "needs_review"
      ? ["◐", "text-attention"]
      : tx.status === "duplicate"
        ? ["○", "text-muted"]
        : ["●", "text-ledger"];
  return (
    <span className={cls}>
      <span aria-hidden="true">{shape}</span>
      <span className="sr-only">{STATUS_LABEL[tx.status]}</span>
    </span>
  );
}

export function TransactionList({
  items,
  selectedId,
  leavingIds,
  categories,
  showCategory,
  onSelect,
}: {
  items: TransactionOut[];
  selectedId: string | null;
  leavingIds?: Set<string>;
  categories: CategoryOut[] | undefined;
  showCategory: boolean;
  onSelect: (id: string) => void;
}) {
  const selRef = useRef<HTMLTableRowElement>(null);
  useEffect(() => {
    selRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [selectedId]);

  return (
    <table className="w-full border-collapse bg-row">
      <caption className="sr-only">Transactions</caption>
      <thead className="sr-only">
        <tr>
          <th>Date</th>
          <th>Description</th>
          {showCategory && <th>Category</th>}
          <th>Amount</th>
        </tr>
      </thead>
      <tbody>
        {items.map((tx) => {
          const selected = tx.id === selectedId;
          const leaving = leavingIds?.has(tx.id);
          return (
            <tr
              key={tx.id}
              ref={selected ? selRef : undefined}
              onClick={() => onSelect(tx.id)}
              className={`cursor-pointer border-b border-rule hover:bg-paper ${leaving ? "row-leave" : ""} ${
                selected ? "bg-paper shadow-[inset_3px_0_0_var(--ledger)]" : ""
              }`}
              data-selected={selected || undefined}
            >
              <td className="w-16 whitespace-nowrap py-2 pl-3 pr-2 text-muted">{shortDate(tx.posted_date)}</td>
              <td className="min-w-0 py-1 pr-2">
                <button
                  type="button"
                  onClick={() => onSelect(tx.id)}
                  aria-current={selected ? "true" : undefined}
                  className="block w-full truncate text-left"
                >
                  {tx.description}
                </button>
                {tx.status === "needs_review" && tx.reasons[0] && (
                  <span className="block truncate text-xs text-attention">{tx.reasons[0]}</span>
                )}
              </td>
              {showCategory && (
                <td className="hidden whitespace-nowrap py-2 pr-2 text-muted sm:table-cell">
                  <StatusMark tx={tx} /> {categoryLabel(categories, tx.category)}
                </td>
              )}
              <td
                className={`num whitespace-nowrap py-2 pr-3 ${tx.amount_cents > 0 ? "text-ledger" : "text-ink"}`}
              >
                {amount(tx.amount_cents)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
