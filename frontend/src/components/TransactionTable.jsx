import { useState } from "react";

const NEEDS_REVIEW = "Needs Review";

export default function TransactionTable({ transactions, categories, onFix, busy, money }) {
  const [onlyReview, setOnlyReview] = useState(false);
  const reviewCount = transactions.filter((t) => t.needs_review).length;
  const rows = onlyReview ? transactions.filter((t) => t.needs_review) : transactions;

  return (
    <section className="card">
      <div className="tabs">
        <button type="button" className={!onlyReview ? "tab active" : "tab"} onClick={() => setOnlyReview(false)}>
          All
        </button>
        <button type="button" className={onlyReview ? "tab active" : "tab"} onClick={() => setOnlyReview(true)}>
          Needs review ({reviewCount})
        </button>
      </div>
      {rows.length === 0 ? (
        <p className="hint">Nothing to review. 🎉</p>
      ) : (
        <div className="scroll">
          <table>
            <thead>
              <tr>
                <th>Date</th><th>Description</th><th className="num">Amount</th><th>Category</th><th>Why</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id} className={t.needs_review ? "review" : ""}>
                  <td>{t.date}</td>
                  <td>{t.description}</td>
                  <td className={t.amount < 0 ? "num" : "num positive"}>{money(t.amount)}</td>
                  <td>
                    <select
                      value={t.category}
                      disabled={busy}
                      aria-label={`Category for ${t.description}`}
                      onChange={(e) => onFix(t.merchant_key, e.target.value)}
                    >
                      {t.needs_review && <option value={NEEDS_REVIEW}>{NEEDS_REVIEW}</option>}
                      {categories.map((c) => (
                        <option key={c} value={c}>
                          {c}
                          {t.suggested_category === c ? " (suggested)" : ""}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="reason">
                    {t.reason}
                    {t.kind === "refund" && <span className="badge">refund</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="hint">Changing a row applies to every row from the same merchant.</p>
    </section>
  );
}
