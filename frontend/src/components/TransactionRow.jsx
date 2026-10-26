import { REVIEW, money } from "../lib/format.js";

export function TransactionRow({ tx, categories, similarPending, onSetCategory, onApplyToMerchant, onRemember }) {
  const needsReview = tx.category === REVIEW;
  const canGeneralize = tx.corrected && tx.category !== REVIEW;

  return (
    <tr className={needsReview ? "needs-review" : tx.corrected ? "corrected" : ""}>
      <td className="nowrap">{tx.date}</td>
      <td>
        <div>{tx.description}</div>
        <div className="meta">
          <span className="merchant">{tx.merchant}</span>
          {tx.flags.map((f) => <span key={f} className={`flag flag-${f}`}>{f}</span>)}
        </div>
      </td>
      <td className={`num ${Number(tx.amount) > 0 ? "in" : ""}`}>{money(tx.amount)}</td>
      <td>
        <select value={tx.category} onChange={(e) => onSetCategory(tx.row, e.target.value)} aria-label={`Category for row ${tx.row}`}>
          {categories.map((c) => <option key={c}>{c}</option>)}
        </select>
        {needsReview && tx.suggestion && (
          <button className="link" onClick={() => onSetCategory(tx.row, tx.suggestion)}>Use suggestion: {tx.suggestion}</button>
        )}
        {canGeneralize && similarPending > 0 && (
          <button className="link" onClick={() => onApplyToMerchant(tx.merchant, tx.category)}>
            Apply to {similarPending} other {tx.merchant} row{similarPending > 1 ? "s" : ""}
          </button>
        )}
        {canGeneralize && (
          <button className="link" onClick={() => onRemember(tx.merchant, tx.category)}>Always use this for {tx.merchant}</button>
        )}
      </td>
      <td className="why">
        {tx.reasons.join("; ")}
        {!needsReview && !tx.corrected && <small> ({Math.round(tx.confidence * 100)}% sure)</small>}
      </td>
    </tr>
  );
}
