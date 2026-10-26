import { formatCurrency, formatDate, formatPercent } from "../format";
import type { Category, SaveCorrection, Transaction } from "../types";
import { CorrectionForm } from "./CorrectionForm";
import { FlagPills } from "./FlagPills";

interface Props {
  transactions: Transaction[];
  categories: Category[];
  currency: string;
  savingId: string | null;
  onSave: SaveCorrection;
}

export function ReviewQueue({ transactions, categories, currency, savingId, onSave }: Props) {
  const rows = transactions.filter((t) => t.status === "needs_review");

  return (
    <section className="card review-queue" aria-labelledby="review-heading">
      <h2 id="review-heading">Needs review ({rows.length})</h2>
      {rows.length === 0 ? (
        <p className="empty success-text">Nothing needs review. Every transaction has a category.</p>
      ) : (
        <>
          <p className="muted">
            These rows could not be categorized with confidence. Pick a category for each one.
          </p>
          <div className="review-list">
            {rows.map((txn) => (
              <article
                key={txn.id}
                className="review-item"
                aria-label={`Review ${txn.description}`}
              >
                <div className="review-info">
                  <div className="review-main">
                    <strong>{txn.description}</strong>
                    <span className={`amount ${txn.spend_amount < 0 ? "credit" : ""}`}>
                      {formatCurrency(txn.amount, txn.currency || currency)}
                    </span>
                  </div>
                  <div className="muted">
                    {formatDate(txn.date)} · {txn.merchant} · {formatPercent(txn.confidence)}{" "}
                    confidence
                  </div>
                  <FlagPills flags={txn.flags} />
                  {txn.reasons.length > 0 && (
                    <ul className="reasons">
                      {txn.reasons.map((reason, i) => (
                        <li key={i}>{reason}</li>
                      ))}
                    </ul>
                  )}
                </div>
                <CorrectionForm
                  txn={txn}
                  categories={categories}
                  saving={savingId === txn.id}
                  onSave={onSave}
                />
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
