import { useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { money, title } from "./api";
import type { Transaction } from "./types";

export default function TransactionTable({
  rows,
  selected,
  onSelect,
}: {
  rows: Transaction[];
  selected: string | undefined;
  onSelect: (row: Transaction) => void;
}) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [page, setPage] = useState(0);
  const [purpose, setPurpose] = useState("all");
  const filtered = rows.filter(
    (row) =>
      (filter === "all" ||
        (filter === "review"
          ? row.needs_review
          : row.review_status === "confirmed")) &&
      (purpose === "all" || row.purpose === purpose) &&
      `${row.description} ${row.category} ${row.account} ${row.amount_minor / 100}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const pageCount = Math.max(1, Math.ceil(filtered.length / 8));
  const activePage = Math.min(page, pageCount - 1);
  const visible = filtered.slice(activePage * 8, activePage * 8 + 8);
  return (
    <section className="transactions-panel">
      <div className="table-toolbar">
        <label className="search">
          <Search size={18} />
          <input
            aria-label="Search transactions"
            placeholder="Search merchant, description or amount…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
          />
        </label>
        <label className="purpose-filter">
          <SlidersHorizontal size={15} />
          <select
            aria-label="Filter purpose"
            value={purpose}
            onChange={(e) => {
              setPurpose(e.target.value);
              setPage(0);
            }}
          >
            <option value="all">All purposes</option>
            {["business", "personal", "mixed", "unknown", "excluded"].map(
              (v) => (
                <option key={v} value={v}>
                  {title(v)}
                </option>
              ),
            )}
          </select>
        </label>
      </div>
      <div className="tabs" role="group" aria-label="Transaction status">
        {[
          ["all", "All transactions", rows.length],
          ["review", "Needs review", rows.filter((r) => r.needs_review).length],
          [
            "confirmed",
            "Confirmed",
            rows.filter((r) => r.review_status === "confirmed").length,
          ],
        ].map(([value, label, count]) => (
          <button
            key={value}
            aria-pressed={filter === value}
            className={filter === value ? "active" : ""}
            onClick={() => {
              setFilter(String(value));
              setPage(0);
            }}
          >
            {label}
            <span>{count}</span>
          </button>
        ))}
      </div>
      <div className="table-scroll">
        <table className="transaction-table">
          <thead>
            <tr>
              <th>Merchant & description</th>
              <th>Date</th>
              <th>Category</th>
              <th>Purpose</th>
              <th className="amount">Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr
                key={row.id}
                className={`${selected === row.id ? "selected " : ""}${row.needs_review ? "review-row" : ""}`}
                onClick={() => onSelect(row)}
              >
                <td>
                  <button
                    className="merchant-cell"
                    aria-label={`Review ${row.description}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelect(row);
                    }}
                  >
                    <span
                      className={`merchant-avatar ${row.purpose === "personal" ? "personal-avatar" : row.kind === "transfer" ? "transfer-avatar" : ""}`}
                    >
                      {row.description.slice(0, 1)}
                    </span>
                    <span>
                      <strong>
                        {row.description.split(" ").slice(0, 3).join(" ")}
                      </strong>
                      <small title={row.description}>{row.description}</small>
                    </span>
                  </button>
                </td>
                <td className="date-cell">
                  {new Date(`${row.date}T12:00:00`).toLocaleDateString(
                    "en-GB",
                    { day: "2-digit", month: "short" },
                  )}
                  <small>{row.date.slice(0, 4)}</small>
                </td>
                <td>
                  <span className="category-label">{row.category}</span>
                </td>
                <td>
                  <span className={`purpose ${row.purpose}`}>
                    {title(row.purpose)}
                  </span>
                </td>
                <td
                  className={`amount ${row.amount_minor < 0 ? "incoming" : ""}`}
                >
                  <span>
                    {row.amount_minor < 0 ? (
                      <ArrowDownLeft size={13} />
                    ) : (
                      <ArrowUpRight size={13} />
                    )}{" "}
                    {money(Math.abs(row.amount_minor), row.currency)}
                  </span>
                  <small>
                    {row.kind === "refund"
                      ? "Refund"
                      : row.amount_minor < 0
                        ? "Money in"
                        : ""}
                  </small>
                </td>
                <td>
                  <span
                    className={`status ${row.needs_review ? "needs-review" : row.review_status === "confirmed" ? "confirmed" : "categorized"}`}
                  >
                    {row.needs_review ? (
                      "Needs review"
                    ) : row.review_status === "confirmed" ? (
                      <>
                        <Check size={12} /> Confirmed
                      </>
                    ) : (
                      "Categorized"
                    )}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!visible.length ? (
          <div className="empty-table">
            <Search size={25} />
            <h3>No matching transactions</h3>
            <p>Try another search or filter.</p>
          </div>
        ) : null}
      </div>
      <footer className="table-footer">
        <span>
          Showing {filtered.length ? activePage * 8 + 1 : 0}–
          {Math.min((activePage + 1) * 8, filtered.length)} of {filtered.length}{" "}
          transactions
        </span>
        <div>
          <button
            className="icon-button"
            aria-label="Previous page"
            disabled={activePage === 0}
            onClick={() => setPage(activePage - 1)}
          >
            <ChevronLeft size={17} />
          </button>
          <span className="page-number">{activePage + 1}</span>
          <span>of {pageCount}</span>
          <button
            className="icon-button"
            aria-label="Next page"
            disabled={activePage === pageCount - 1}
            onClick={() => setPage(activePage + 1)}
          >
            <ChevronRight size={17} />
          </button>
        </div>
      </footer>
    </section>
  );
}
