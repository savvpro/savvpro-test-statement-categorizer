import { useState } from "react";
import { formatMoney } from "../utils";

function optionsFor(row, categories) {
  const seen = new Set();
  const list = [];
  for (const c of [...(row.candidates ?? []), ...categories]) {
    if (!seen.has(c)) {
      seen.add(c);
      list.push(c);
    }
  }
  if (!row.needs_review && !seen.has(row.category)) list.unshift(row.category);
  return list;
}

export default function TransactionTable({ rows, categories, onFix, busy }) {
  const [filter, setFilter] = useState("all");
  const reviewCount = rows.filter((r) => r.needs_review).length;
  const shown = filter === "review" ? rows.filter((r) => r.needs_review) : rows;

  return (
    <section className="panel">
      <div className="tabs">
        <button className={filter === "all" ? "tab active" : "tab"} onClick={() => setFilter("all")}>
          All ({rows.length})
        </button>
        <button className={filter === "review" ? "tab active" : "tab"} onClick={() => setFilter("review")}>
          Needs review ({reviewCount})
        </button>
      </div>

      {shown.length === 0 ? (
        <p className="muted">Nothing to show here.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Line</th><th>Date</th><th>Description</th>
                <th className="num">Amount</th><th>Category</th><th>Why</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr key={r.row} className={r.needs_review ? "review" : ""}>
                  <td>{r.row}</td>
                  <td>{r.date}</td>
                  <td>
                    {r.description}
                    {r.possible_duplicate && <span className="badge">possible duplicate</span>}
                  </td>
                  <td className={`num ${Number(r.amount) < 0 ? "neg" : "pos"}`}>
                    {formatMoney(r.amount)}
                  </td>
                  <td>
                    <select
                      value={r.needs_review ? "" : r.category}
                      disabled={busy}
                      aria-label={`Category for ${r.description}`}
                      onChange={(e) => e.target.value && onFix(r.merchant_key, e.target.value)}
                    >
                      {r.needs_review && <option value="" disabled>Choose category…</option>}
                      {optionsFor(r, categories).map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </td>
                  <td className="muted small">{r.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="muted small">
        Changing a category applies to every row from the same merchant.
      </p>
    </section>
  );
}