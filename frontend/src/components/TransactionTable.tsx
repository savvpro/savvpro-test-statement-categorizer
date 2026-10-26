import { Fragment, useMemo, useState } from "react";
import { formatCurrency, formatDate, formatPercent, pluralize } from "../format";
import type { Category, SaveCorrection, Transaction } from "../types";
import { CorrectionForm } from "./CorrectionForm";
import { FlagPills } from "./FlagPills";
import { StatusBadge } from "./StatusBadge";

type FilterKey = "all" | "needs_review" | "categorized" | "excluded" | "user_corrected" | "flagged";
type SortKey = "date" | "amount";
type SortDir = "asc" | "desc";
type RowMode = "details" | "edit";

const FILTERS: { key: FilterKey; label: string; test: (t: Transaction) => boolean }[] = [
  { key: "all", label: "All", test: () => true },
  { key: "needs_review", label: "Needs review", test: (t) => t.status === "needs_review" },
  { key: "categorized", label: "Categorized", test: (t) => t.status === "categorized" },
  { key: "excluded", label: "Excluded", test: (t) => t.status === "excluded" },
  { key: "user_corrected", label: "Corrected", test: (t) => t.status === "user_corrected" },
  { key: "flagged", label: "Flagged", test: (t) => t.flags.length > 0 },
];

interface Props {
  transactions: Transaction[];
  categories: Category[];
  currency: string;
  savingId: string | null;
  onSave: SaveCorrection;
}

function matchesSearch(t: Transaction, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return [t.description, t.merchant, t.category_name, t.date, t.amount.toFixed(2)].some((v) =>
    v.toLowerCase().includes(q),
  );
}

export function TransactionTable({ transactions, categories, currency, savingId, onSave }: Props) {
  const [filter, setFilter] = useState<FilterKey>("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir } | null>(null);
  const [open, setOpen] = useState<Record<string, RowMode | undefined>>({});

  const counts = useMemo(
    () => Object.fromEntries(FILTERS.map((f) => [f.key, transactions.filter(f.test).length])),
    [transactions],
  );

  const rows = useMemo(() => {
    const active = FILTERS.find((f) => f.key === filter) ?? FILTERS[0];
    const list = transactions.filter((t) => active.test(t) && matchesSearch(t, search));
    if (!sort) return list;
    const factor = sort.dir === "asc" ? 1 : -1;
    return [...list].sort((a, b) => {
      const diff = sort.key === "date" ? a.date.localeCompare(b.date) : a.amount - b.amount;
      return diff !== 0 ? diff * factor : a.line - b.line;
    });
  }, [transactions, filter, search, sort]);

  function toggleSort(key: SortKey) {
    setSort((prev) => {
      if (!prev || prev.key !== key) return { key, dir: "asc" };
      return prev.dir === "asc" ? { key, dir: "desc" } : null;
    });
  }

  function toggleRow(id: string, mode: RowMode) {
    setOpen((prev) => ({ ...prev, [id]: prev[id] === mode ? undefined : mode }));
  }

  function ariaSort(key: SortKey): "ascending" | "descending" | "none" {
    if (sort?.key !== key) return "none";
    return sort.dir === "asc" ? "ascending" : "descending";
  }

  function arrow(key: SortKey): string {
    if (sort?.key !== key) return "↕";
    return sort.dir === "asc" ? "↑" : "↓";
  }

  return (
    <section className="card" aria-labelledby="txn-heading">
      <h2 id="txn-heading">Transactions</h2>

      <div className="toolbar">
        <div className="chips" role="group" aria-label="Filter transactions">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              type="button"
              className="chip"
              aria-pressed={filter === f.key}
              onClick={() => setFilter(f.key)}
            >
              {f.label} <span className="chip-count">{counts[f.key]}</span>
            </button>
          ))}
        </div>
        <div className="field search">
          <label htmlFor="txn-search">Search</label>
          <input
            id="txn-search"
            type="search"
            value={search}
            placeholder="Description, merchant, category"
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <p className="muted" aria-live="polite">
        Showing {rows.length} of {pluralize(transactions.length, "transaction")}
      </p>

      {transactions.length === 0 ? (
        <p className="empty">This statement has no transactions.</p>
      ) : (
        <div className="table-scroll tall">
          <table className="txn-table">
            <thead>
              <tr>
                <th scope="col" aria-sort={ariaSort("date")}>
                  <button type="button" className="sort" onClick={() => toggleSort("date")}>
                    Date <span aria-hidden="true">{arrow("date")}</span>
                  </button>
                </th>
                <th scope="col">Description</th>
                <th scope="col" className="num" aria-sort={ariaSort("amount")}>
                  <button type="button" className="sort" onClick={() => toggleSort("amount")}>
                    Amount <span aria-hidden="true">{arrow("amount")}</span>
                  </button>
                </th>
                <th scope="col">Category</th>
                <th scope="col">Status</th>
                <th scope="col" className="num">
                  Confidence
                </th>
                <th scope="col">Flags</th>
                <th scope="col">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr>
                  <td colSpan={8} className="empty">
                    No transactions match the current filter.
                  </td>
                </tr>
              )}
              {rows.map((t) => {
                const mode = open[t.id];
                return (
                  <Fragment key={t.id}>
                    <tr className={`status-row-${t.status}`}>
                      <td className="nowrap">{formatDate(t.date)}</td>
                      <td>
                        <div>{t.description}</div>
                        <div className="muted small">{t.merchant}</div>
                      </td>
                      <td className={`num ${t.spend_amount < 0 ? "credit" : ""}`}>
                        {formatCurrency(t.amount, t.currency || currency)}
                      </td>
                      <td>{t.category_name}</td>
                      <td>
                        <StatusBadge status={t.status} />
                      </td>
                      <td className="num">{formatPercent(t.confidence)}</td>
                      <td>
                        <FlagPills flags={t.flags} />
                      </td>
                      <td className="actions">
                        <button
                          type="button"
                          className="button small"
                          aria-expanded={mode === "details"}
                          aria-label={`Details for ${t.description}`}
                          onClick={() => toggleRow(t.id, "details")}
                        >
                          Details
                        </button>
                        <button
                          type="button"
                          className="button small"
                          aria-expanded={mode === "edit"}
                          aria-label={`Edit category for ${t.description}`}
                          onClick={() => toggleRow(t.id, "edit")}
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                    {mode && (
                      <tr className="detail-row">
                        <td colSpan={8}>
                          {mode === "details" ? (
                            <div className="details">
                              <h3>Why this category</h3>
                              {t.reasons.length === 0 ? (
                                <p className="muted">No explanation recorded.</p>
                              ) : (
                                <ul className="reasons">
                                  {t.reasons.map((r, i) => (
                                    <li key={i}>{r}</li>
                                  ))}
                                </ul>
                              )}
                              <p className="muted small">
                                Line {t.line} of the file
                                {t.refund_of ? ` · refund of ${t.refund_of}` : ""}
                              </p>
                            </div>
                          ) : (
                            <CorrectionForm
                              txn={t}
                              categories={categories}
                              saving={savingId === t.id}
                              onSave={onSave}
                            />
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
