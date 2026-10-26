import { useMemo, useState } from "react";
import { displayDate, money } from "../api";
import type { Transaction } from "../types";
import { Icon } from "./Icon";

export type Filter = "all" | "needs_review" | "accepted" | "excluded";
const PAGE_SIZE = 8;
export function TransactionTable({
  rows,
  filter,
  onFilter,
  onReview,
}: {
  rows: Transaction[];
  filter: Filter;
  onFilter: (filter: Filter) => void;
  onReview: (row: Transaction) => void;
}) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("source");
  const filtered = useMemo(
    () =>
      rows
        .filter((row) => {
          const matches =
            filter === "all" ||
            (filter === "excluded"
              ? row.excluded
              : filter === "needs_review"
                ? row.status === "needs_review"
                : row.status !== "needs_review" && !row.excluded);
          return (
            matches &&
            `${row.description} ${row.category} ${row.date}`
              .toLowerCase()
              .includes(search.toLowerCase())
          );
        })
        .sort((a, b) =>
          sort === "amount"
            ? a.amount_minor - b.amount_minor
            : sort === "date"
              ? b.date.localeCompare(a.date) || a.source_row - b.source_row
              : a.source_row - b.source_row,
        ),
    [rows, filter, search, sort],
  );
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const visible = filtered.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE,
  );
  const filters: { value: Filter; label: string; count: number }[] = [
    { value: "all", label: "All transactions", count: rows.length },
    {
      value: "needs_review",
      label: "Needs review",
      count: rows.filter((row) => row.status === "needs_review").length,
    },
    {
      value: "accepted",
      label: "Accepted",
      count: rows.filter(
        (row) => row.status !== "needs_review" && !row.excluded,
      ).length,
    },
    {
      value: "excluded",
      label: "Excluded",
      count: rows.filter((row) => row.excluded).length,
    },
  ];
  return (
    <section
      className="panel transaction-panel"
      aria-labelledby="transactions-heading"
    >
      <div className="section-top table-heading">
        <div>
          <h2 id="transactions-heading">Transactions</h2>
          <p className="small muted">
            The original rows, with a reason behind every decision.
          </p>
        </div>
        <span className="small muted">{rows.length} rows imported</span>
      </div>
      <div className="table-controls">
        <div className="filter-tabs" aria-label="Filter transactions">
          {filters.map((item) => (
            <button
              key={item.value}
              className={filter === item.value ? "active" : ""}
              aria-pressed={filter === item.value}
              onClick={() => {
                onFilter(item.value);
                setPage(1);
              }}
            >
              {item.label}
              <span>{item.count}</span>
            </button>
          ))}
        </div>
        <div className="search">
          <Icon name="search" size={17} />
          <input
            type="search"
            placeholder="Search transactions"
            aria-label="Search transactions"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>
      <div className="sort-row">
        <span className="small muted">
          Negative = money out · Positive = money in
        </span>
        <label className="sort-label">
          Sort by
          <select
            value={sort}
            onChange={(event) => {
              setSort(event.target.value);
              setPage(1);
            }}
          >
            <option value="source">Statement order</option>
            <option value="date">Newest date</option>
            <option value="amount">Amount: low to high</option>
          </select>
        </label>
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
                <span className="sr-only">Action</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={row.id} className={row.excluded ? "excluded-row" : ""}>
                <td>
                  <div className="merchant-cell">
                    <span
                      className={`merchant-icon ${row.kind === "transfer" ? "transfer" : row.kind === "refund" ? "refund" : ""}`}
                    >
                      {row.kind === "transfer"
                        ? "↔"
                        : row.kind === "refund"
                          ? "↩"
                          : row.description
                              .replace(/[^a-zA-Z]/g, "")
                              .slice(0, 2)
                              .toUpperCase() || "•"}
                    </span>
                    <div>
                      <strong>{row.description}</strong>
                      <small>
                        Row {row.source_row}
                        {row.review_flags.length > 0 &&
                          ` · ${row.review_flags.map((flag) => flag.replaceAll("_", " ")).join(", ")}`}
                        {row.kind === "refund" && " · Refund"}
                      </small>
                    </div>
                  </div>
                </td>
                <td className="date-cell">{displayDate(row.date)}</td>
                <td>
                  <span
                    className={`category-tag ${row.category === "Needs Review" ? "unknown" : ""}`}
                  >
                    {row.category}
                  </span>
                </td>
                <td>
                  <span
                    className={`status ${row.excluded ? "excluded" : row.status}`}
                  >
                    <span className="status-dot" />
                    {row.excluded
                      ? "Excluded"
                      : row.status === "auto"
                        ? "Auto-sorted"
                        : row.status === "reviewed"
                          ? "Reviewed"
                          : "Needs review"}
                  </span>
                </td>
                <td
                  className={`amount ${row.amount_minor > 0 ? "positive" : ""}`}
                >
                  {row.amount_minor > 0 ? "+" : ""}
                  {money(row.amount_minor, row.currency)}
                </td>
                <td>
                  <button
                    className="icon-button row-action"
                    aria-label={`Review ${row.description}, row ${row.source_row}`}
                    onClick={() => onReview(row)}
                  >
                    <Icon name="chevron" size={17} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {visible.length === 0 && (
          <div className="empty-results">
            <Icon name="check" size={25} />
            <h3>
              {filter === "needs_review" && !search
                ? "All caught up."
                : "No matching transactions"}
            </h3>
            <p className="muted">
              {filter === "needs_review" && !search
                ? "Every row has a decision. Your final export is ready."
                : "Try another search or filter."}
            </p>
          </div>
        )}
      </div>
      <div className="table-footer">
        <span>
          {filtered.length
            ? `${(currentPage - 1) * PAGE_SIZE + 1}–${Math.min(currentPage * PAGE_SIZE, filtered.length)}`
            : "0"}{" "}
          of {filtered.length} transactions
        </span>
        <div>
          <button
            className="button small-button secondary"
            onClick={() => setPage(currentPage - 1)}
            disabled={currentPage === 1}
          >
            Previous
          </button>
          <span>
            Page {currentPage} of {totalPages}
          </span>
          <button
            className="button small-button secondary"
            onClick={() => setPage(currentPage + 1)}
            disabled={currentPage === totalPages}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}
