import { useMemo, useState } from "react";
import { countByFilter, FILTERS, filterTransactions, type FilterId } from "../lib/filters";
import type { Category, Transaction } from "../types";
import { TransactionRow } from "./TransactionRow";

interface Props {
  transactions: Transaction[];
  categories: Category[];
  categoryMap: Map<string, Category>;
  busy: boolean;
  remember: boolean;
  onRememberChange: (value: boolean) => void;
  onChange: (tx: Transaction, category: string | null) => void;
}

export function TransactionTable({
  transactions,
  categories,
  categoryMap,
  busy,
  remember,
  onRememberChange,
  onChange,
}: Props) {
  const counts = useMemo(
    () => countByFilter(transactions, categoryMap),
    [transactions, categoryMap],
  );
  const [filter, setFilter] = useState<FilterId>(counts.review > 0 ? "review" : "all");
  const [query, setQuery] = useState("");
  const visible = useMemo(
    () => filterTransactions(transactions, filter, query, categoryMap),
    [transactions, filter, query, categoryMap],
  );

  return (
    <section className="panel panel--flush" aria-labelledby="tx-title">
      <div className="tx-toolbar">
        <h2 id="tx-title">Transactions</h2>
        <div className="tabs" role="tablist">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              role="tab"
              aria-selected={filter === f.id}
              className={`tab${filter === f.id ? " is-active" : ""}${
                f.id === "review" && counts.review > 0 ? " tab--warn" : ""
              }`}
              onClick={() => setFilter(f.id)}
            >
              {f.label} <span className="tab__count">{counts[f.id]}</span>
            </button>
          ))}
        </div>
        <div className="tx-toolbar__row">
          <input
            type="search"
            placeholder="Search merchant or category"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search transactions"
          />
          <label className="checkbox">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => onRememberChange(e.target.checked)}
            />
            Remember my choices for the same merchant
          </label>
        </div>
      </div>

      {visible.length === 0 ? (
        <p className="empty">
          {filter === "review" ? "🎉 Nothing left to review." : "No transactions match."}
        </p>
      ) : (
        <div className="table-scroll">
          <table className="tx-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Description</th>
                <th className="num">Amount</th>
                <th>Category</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((tx) => (
                <TransactionRow
                  key={tx.id}
                  tx={tx}
                  categories={categories}
                  categoryMap={categoryMap}
                  busy={busy}
                  onChange={onChange}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
