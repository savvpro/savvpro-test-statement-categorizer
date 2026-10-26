import { useMemo } from "react";
import { REVIEW } from "../lib/format.js";
import { TransactionRow } from "./TransactionRow.jsx";

export function TransactionTable({ rows, categories, filters, ...actions }) {
  const pendingByMerchant = useMemo(() => {
    const counts = new Map();
    rows.filter((r) => r.category === REVIEW && !r.flags.includes("duplicate"))
      .forEach((r) => counts.set(r.merchant, (counts.get(r.merchant) || 0) + 1));
    return counts;
  }, [rows]);

  const query = filters.query.trim().toLowerCase();
  const visible = rows.filter((r) =>
    (!filters.reviewOnly || r.category === REVIEW || r.corrected) &&
    (!filters.category || r.category === filters.category) &&
    (!query || r.description.toLowerCase().includes(query) || r.merchant.toLowerCase().includes(query))
  );

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr><th>Date</th><th>Description</th><th className="num">Amount</th><th>Category</th><th>Why</th></tr>
        </thead>
        <tbody>
          {visible.map((tx) => (
            <TransactionRow key={tx.row} tx={tx} categories={categories}
              similarPending={pendingByMerchant.get(tx.merchant) || 0} {...actions} />
          ))}
          {!visible.length && <tr><td colSpan={5} className="empty">No transactions match these filters.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
