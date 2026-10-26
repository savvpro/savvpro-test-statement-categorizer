import { useEffect, useMemo, useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { money, shortDate } from "../api";
import { allCategories, type Statement, type Transaction } from "../types";

export type Filter = "all" | "needs_review" | "reviewed";
export function TransactionTable({
  statement,
  onReview,
  filter,
  setFilter,
  category,
  setCategory,
}: {
  statement: Statement;
  onReview: (transaction: Transaction) => void;
  filter: Filter;
  setFilter: (filter: Filter) => void;
  category: string;
  setCategory: (category: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [order, setOrder] = useState("source");
  useEffect(() => {
    setPage(0);
  }, [search, filter, category, statement.id, order]);
  const rows = useMemo(() => {
    const list = statement.transactions.filter(
      (row) =>
        (filter === "all" || row.status === filter) &&
        (!category || row.category === category) &&
        `${row.description} ${row.category ?? ""} ${row.source_id}`
          .toLowerCase()
          .includes(search.toLowerCase()),
    );
    if (order === "newest") list.sort((a, b) => b.date.localeCompare(a.date));
    if (order === "largest")
      list.sort((a, b) => Math.abs(b.amount_cents) - Math.abs(a.amount_cents));
    return list;
  }, [statement.transactions, filter, category, search, order]);
  const pages = Math.max(1, Math.ceil(rows.length / 12));
  const currentPage = Math.min(page, pages - 1);
  const visible = rows.slice(currentPage * 12, currentPage * 12 + 12);
  return (
    <section className="panel transactions-panel" id="transactions">
      <div className="panel-title">
        <div>
          <h2>Your transactions</h2>
          <p>A clear category. A reason behind every decision.</p>
        </div>
        <span className="count-label">
          {statement.transactions.length} total
        </span>
      </div>
      <div className="table-toolbar">
        <div className="tabs" aria-label="Transaction status">
          <button
            className={filter === "all" ? "active" : ""}
            onClick={() => setFilter("all")}
          >
            All transactions
          </button>
          <button
            className={filter === "needs_review" ? "active" : ""}
            onClick={() => setFilter("needs_review")}
          >
            Needs review <span>{statement.summary.needs_review}</span>
          </button>
          <button
            className={filter === "reviewed" ? "active" : ""}
            onClick={() => setFilter("reviewed")}
          >
            Reviewed
          </button>
        </div>
        <div className="table-controls">
          <label className="search-field">
            <Search size={16} />
            <input
              aria-label="Search transactions"
              placeholder="Search transactions…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          <label className="filter-field">
            <SlidersHorizontal size={15} />
            <select
              aria-label="Filter by category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="">All categories</option>
              {allCategories.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <select
            aria-label="Sort transactions"
            value={order}
            onChange={(e) => setOrder(e.target.value)}
          >
            <option value="source">Statement order</option>
            <option value="newest">Newest first</option>
            <option value="largest">Largest amount</option>
          </select>
        </div>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Transaction</th>
              <th>Date</th>
              <th>Category</th>
              <th>Status</th>
              <th className="amount">Amount</th>
              <th>
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr
                key={row.id}
                className={row.status === "needs_review" ? "pending-row" : ""}
              >
                <td>
                  <div className="merchant">
                    <div
                      className={`merchant-icon ${row.amount_cents > 0 ? "incoming" : ""}`}
                    >
                      {row.amount_cents > 0 ? (
                        <ArrowDownLeft size={17} />
                      ) : (
                        <ArrowUpRight size={17} />
                      )}
                    </div>
                    <div>
                      <span className="merchant-name" title={row.description}>
                        {row.description}
                      </span>
                      <span className="merchant-meta">
                        {row.duplicate_of
                          ? `Possible duplicate · row ${row.row_number}`
                          : row.kind === "credit"
                            ? "Incoming payment"
                            : row.kind.charAt(0).toUpperCase() +
                              row.kind.slice(1)}
                      </span>
                    </div>
                  </div>
                </td>
                <td className="date-cell">
                  {shortDate(row.date)}
                  <span className="merchant-meta">{row.date.slice(0, 4)}</span>
                </td>
                <td>
                  <span
                    className={`category-pill ${row.category ? "" : "uncategorized"}`}
                  >
                    {row.category || "Uncategorized"}
                  </span>
                </td>
                <td>
                  <span className={`status ${row.status}`}>
                    {row.status === "needs_review" ? (
                      <i />
                    ) : (
                      <Check size={12} />
                    )}
                    {row.status === "needs_review"
                      ? "Needs review"
                      : row.status === "reviewed"
                        ? "Reviewed"
                        : "Categorized"}
                  </span>
                </td>
                <td
                  className={`amount ${row.amount_cents > 0 ? "positive" : ""}`}
                >
                  {row.amount_cents > 0 ? "+" : ""}
                  {money(row.amount_cents, statement.currency)}
                </td>
                <td>
                  <button
                    className={`row-action ${row.status === "needs_review" ? "action-review" : ""}`}
                    onClick={() => onReview(row)}
                    aria-label={`Review ${row.description}`}
                  >
                    {row.status === "needs_review" ? "Review" : "Details"}
                    <ChevronRight size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!rows.length && (
        <div className="small-empty">
          <Search size={24} />
          <h3>No matching transactions</h3>
          <p>Try another search or change the filters.</p>
          <button
            className="text-button"
            onClick={() => {
              setSearch("");
              setFilter("all");
              setCategory("");
            }}
          >
            Clear filters
          </button>
        </div>
      )}
      <div className="table-footer">
        <span>
          {rows.length
            ? `${currentPage * 12 + 1}–${Math.min((currentPage + 1) * 12, rows.length)}`
            : "0"}{" "}
          of {rows.length} transactions
        </span>
        <div>
          <button
            className="icon-button"
            aria-label="Previous page"
            disabled={currentPage === 0}
            onClick={() => setPage(currentPage - 1)}
          >
            <ChevronLeft size={17} />
          </button>
          <span>
            {currentPage + 1} / {pages}
          </span>
          <button
            className="icon-button"
            aria-label="Next page"
            disabled={currentPage + 1 >= pages}
            onClick={() => setPage(currentPage + 1)}
          >
            <ChevronRight size={17} />
          </button>
        </div>
      </div>
    </section>
  );
}
