import { useEffect, useRef, useState } from "react";
import { api, displayDate, errorMessage, money } from "../api";
import {
  categories,
  type Category,
  type Kind,
  type ReviewInput,
  type Transaction,
} from "../types";
import { Icon } from "./Icon";

export function ReviewDialog({
  transaction,
  onClose,
  onSaved,
}: {
  transaction: Transaction;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [category, setCategory] = useState<Category>(transaction.category);
  const [kind, setKind] = useState<Kind>(transaction.kind);
  const [excluded, setExcluded] = useState(transaction.excluded);
  const [note, setNote] = useState(transaction.note);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    dialog.current?.showModal();
    const node = dialog.current;
    return () => node?.close();
  }, []);

  function chooseCategory(value: Category) {
    setCategory(value);
    const special: Partial<Record<Category, Kind>> = {
      Income: "income",
      Transfers: "transfer",
      Personal: "personal",
      "Needs Review": "unknown",
    };
    setKind(
      special[value] ?? (transaction.amount_minor > 0 ? "refund" : "expense"),
    );
  }

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const payload: ReviewInput = {
      category,
      kind,
      excluded,
      note,
      expected_version: transaction.version,
    };
    try {
      await api.review(transaction.id, payload);
      await onSaved();
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <dialog
      ref={dialog}
      className="review-dialog"
      aria-labelledby="review-title"
      onCancel={(event) => {
        if (busy) event.preventDefault();
        else onClose();
      }}
    >
      <form onSubmit={save}>
        <div className="section-top">
          <span className="eyebrow">
            TRANSACTION REVIEW · ROW {transaction.source_row}
          </span>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Close review"
            disabled={busy}
          >
            <Icon name="close" />
          </button>
        </div>
        <h2 id="review-title">{transaction.description}</h2>
        <div className="review-amount">
          {money(transaction.amount_minor, transaction.currency)}{" "}
          <span>
            {displayDate(transaction.date)} · {transaction.currency}
          </span>
        </div>
        <div className="reason-box">
          <span className="eyebrow">WHY IT LANDED HERE</span>
          <p>{transaction.reason}</p>
          <span className="small muted">
            Rule: {transaction.rule_id} · Strength:{" "}
            {Math.round(transaction.confidence * 100)}/100
          </span>
        </div>
        {transaction.review_flags.length > 0 && (
          <p className="small amber-text">
            Flags:{" "}
            {transaction.review_flags
              .map((flag) => flag.replaceAll("_", " "))
              .join(" · ")}
          </p>
        )}
        <fieldset disabled={busy} className="form-fields">
          <div className="form-grid two">
            <label>
              Category
              <select
                value={category}
                onChange={(event) =>
                  chooseCategory(event.target.value as Category)
                }
                disabled={excluded}
              >
                {categories.map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
            </label>
            <label>
              Money movement
              <select
                value={kind}
                onChange={(event) => setKind(event.target.value as Kind)}
                disabled={excluded}
              >
                <option value="unknown">Choose movement</option>
                <option value="expense">Expense · money out</option>
                <option value="refund">Refund · money back</option>
                <option value="income">Income · client payment</option>
                <option value="transfer">Transfer · not spending</option>
                <option value="personal">Personal · not business</option>
              </select>
            </label>
          </div>
          <label className="check-label">
            <input
              type="checkbox"
              checked={excluded}
              onChange={(event) => setExcluded(event.target.checked)}
            />
            <span>
              Exclude this row from totals
              <small>
                For duplicate entries, pending charges, or invalid rows.
              </small>
            </span>
          </label>
          <label>
            Review note {excluded ? "(required)" : "(optional)"}
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              maxLength={1000}
              rows={3}
              required={excluded}
              placeholder="e.g. Duplicate of the charge on row 17"
            />
          </label>
          <p className="small muted">
            Your decision is saved with a versioned audit record. It won’t
            create a rule for other transactions.
          </p>
          {error && (
            <div className="error-box" role="alert">
              {error}
            </div>
          )}
          <div className="dialog-actions">
            <button
              type="button"
              className="button secondary"
              onClick={onClose}
            >
              Cancel
            </button>
            <button className="button primary" type="submit">
              {busy ? "Saving…" : "Save decision"}
              <Icon name="check" size={17} />
            </button>
          </div>
        </fieldset>
      </form>
    </dialog>
  );
}
