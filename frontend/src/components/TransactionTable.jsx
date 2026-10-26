import { useMemo, useState } from "react";
import CategorySelect from "./CategorySelect";
import { formatMoney, getCategoryTone } from "../constants/categories";

const PAGE_SIZE = 20;
const CONF_RANK = { low: 0, medium: 1, high: 2 };

const COLUMNS = [
  { key: "date", label: "Date" },
  { key: "description", label: "Description" },
  { key: "amount", label: "Amount" },
  { key: "category", label: "Category" },
  { key: "confidence", label: "Confidence" },
  { key: "reason", label: "Reason" },
];

// Works with "high"/"medium"/"low" strings or a 0-1 number.
function confLevel(c) {
  const n = typeof c === "number" ? c : Number(c);
  if (c !== "" && c !== null && !Number.isNaN(n)) {
    return n >= 0.8 ? "high" : n >= 0.5 ? "medium" : "low";
  }
  return String(c ?? "").toLowerCase();
}

function sortValue(t, key) {
  switch (key) {
    case "description":
      return (t.raw_description || "").toLowerCase();
    case "category":
      return (t.category || "").toLowerCase();
    case "reason":
      return (t.reason || "").toLowerCase();
    case "confidence":
      return CONF_RANK[confLevel(t.confidence)] ?? 1;
    default:
      return t[key];
  }
}

function pageList(page, pages) {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1);
  const set = new Set([1, pages, page - 1, page, page + 1]);
  const nums = [...set].filter((n) => n >= 1 && n <= pages).sort((a, b) => a - b);
  const out = [];
  nums.forEach((n, i) => {
    if (i && n - nums[i - 1] > 1) out.push("…");
    out.push(n);
  });
  return out;
}

export default function TransactionTable({ transactions, categories, onChange, savingId }) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState({ key: null, dir: "asc" });
  const [page, setPage] = useState(1);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = q
      ? transactions.filter((t) =>
          [t.raw_description, t.category, t.reason, t.date]
            .join(" ")
            .toLowerCase()
            .includes(q)
        )
      : transactions;
    if (sort.key) {
      const dir = sort.dir === "asc" ? 1 : -1;
      list = [...list].sort((a, b) => {
        const x = sortValue(a, sort.key);
        const y = sortValue(b, sort.key);
        return (x > y ? 1 : x < y ? -1 : 0) * dir;
      });
    }
    return list;
  }, [transactions, query, sort]);

  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const current = Math.min(page, pages);
  const start = (current - 1) * PAGE_SIZE;
  const visible = rows.slice(start, start + PAGE_SIZE);

  function toggleSort(key) {
    setSort((s) =>
      s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }
    );
  }

  return (
    <section className="card">
      <div className="step-head spread">
        <div className="step-head-left">
          <span className="step">2</span>
          <div>
            <h2>Review Categorized Transactions</h2>
            <p>
              Each row was sorted by our rules. Rows marked Needs Review are uncertain, so pick
              the right category from the dropdown.
            </p>
          </div>
        </div>
        <div className="table-tools">
          <span className="count-pill">Total Transactions: {transactions.length}</span>
          {transactions.some((t) => t.category === "Needs Review") && (
            <span className="count-pill warn">
              Needs Review: {transactions.filter((t) => t.category === "Needs Review").length}
            </span>
          )}
          <label className="search">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20l-3.5-3.5" />
            </svg>
            <input
              type="search"
              placeholder="Search transactions..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
            />
          </label>
        </div>
      </div>

      <div className="table-wrap">
        <table className="tx">
          <thead>
            <tr>
              {COLUMNS.map((c) => (
                <th
                  key={c.key}
                  onClick={() => toggleSort(c.key)}
                  aria-sort={
                    sort.key === c.key ? (sort.dir === "asc" ? "ascending" : "descending") : "none"
                  }
                >
                  <span className="th-inner">
                    {c.label}
                    <span className={sort.key === c.key ? "sort on" : "sort"}>
                      {sort.key === c.key ? (sort.dir === "asc" ? "↑" : "↓") : "↕"}
                    </span>
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((t) => {
              const tone = getCategoryTone(t.category);
              const level = confLevel(t.confidence);
              const desc = t.raw_description || "";
              return (
                <tr key={t.id} className={t.category === "Needs Review" ? "review" : ""}>
                  <td className="nowrap">{t.date}</td>
                  <td>
                    <div className="desc">
                      <span className="mono-avatar" style={{ background: tone.bg, color: tone.fg }}>
                        {desc.trim().charAt(0).toUpperCase() || "?"}
                      </span>
                      <span className="desc-text">{desc}</span>
                      {t.user_overridden && <span className="badge">edited</span>}
                    </div>
                  </td>
                  <td className={(t.amount < 0 ? "neg" : "pos") + " amount nowrap"}>
                    {t.amount < 0 ? "- " : "+ "}
                    {formatMoney(Math.abs(t.amount))} {t.currency}
                  </td>
                  <td>
                    <CategorySelect
                      value={t.category}
                      categories={categories}
                      disabled={savingId === t.id}
                      onChange={(c) => onChange(t.id, c)}
                    />
                  </td>
                  <td>
                    <span className={"conf " + level}>
                      <i />
                      {String(t.confidence).charAt(0).toUpperCase() + String(t.confidence).slice(1)}
                    </span>
                  </td>
                  <td className="reason">{t.reason}</td>
                </tr>
              );
            })}
            {visible.length === 0 && (
              <tr>
                <td colSpan={COLUMNS.length} className="empty">
                  No transactions match your search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="pager">
        <span className="pager-info">
          {rows.length === 0
            ? "Showing 0 transactions"
            : `Showing ${start + 1}–${Math.min(start + PAGE_SIZE, rows.length)} of ${rows.length} transactions`}
        </span>
        {pages > 1 && (
          <div className="pager-btns">
            <button
              type="button"
              className="pg"
              disabled={current === 1}
              onClick={() => setPage(current - 1)}
              aria-label="Previous page"
            >
              ‹
            </button>
            {pageList(current, pages).map((n, i) =>
              n === "…" ? (
                <span key={"e" + i} className="pg-gap">…</span>
              ) : (
                <button
                  key={n}
                  type="button"
                  className={n === current ? "pg active" : "pg"}
                  onClick={() => setPage(n)}
                >
                  {n}
                </button>
              )
            )}
            <button
              type="button"
              className="pg"
              disabled={current === pages}
              onClick={() => setPage(current + 1)}
              aria-label="Next page"
            >
              ›
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
