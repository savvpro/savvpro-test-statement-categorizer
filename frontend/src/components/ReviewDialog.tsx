import { useEffect, useRef, useState } from "react";
import { Check, Info, LoaderCircle, X } from "lucide-react";
import { money, shortDate } from "../api";
import {
  expenseCategories,
  type Kind,
  type ReviewInput,
  type Transaction,
} from "../types";

export function ReviewDialog({
  row,
  currency,
  onClose,
  onSave,
}: {
  row: Transaction;
  currency: string;
  onClose: () => void;
  onSave: (input: ReviewInput) => Promise<void>;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [kind, setKind] = useState<Kind | "">(
    row.kind === "credit" ? "" : row.kind,
  );
  const [category, setCategory] = useState(row.category || "");
  const [note, setNote] = useState(row.note);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  const categories =
    kind === "expense" || kind === "refund"
      ? expenseCategories
      : kind === "income"
        ? ["Client income"]
        : kind === "transfer"
          ? ["Transfer"]
          : kind === "personal"
            ? ["Personal"]
            : kind === "excluded"
              ? ["Excluded"]
              : [];
  const changeKind = (value: Kind | "") => {
    setKind(value);
    setCategory(
      value === "income"
        ? "Client income"
        : value === "transfer"
          ? "Transfer"
          : value === "personal"
            ? "Personal"
            : value === "excluded"
              ? "Excluded"
              : "",
    );
  };
  async function save() {
    if (!kind || kind === "credit" || !category) return;
    setSaving(true);
    setError("");
    try {
      await onSave({ kind, category, note, revision: row.revision });
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not save. Please retry.",
      );
    } finally {
      setSaving(false);
    }
  }
  return (
    <dialog
      ref={dialog}
      className="modal review-modal"
      aria-labelledby="review-title"
      onCancel={(e) => {
        e.preventDefault();
        if (!saving) onClose();
      }}
    >
      <div className="modal-heading">
        <div>
          <p className="eyebrow">TRANSACTION DETAILS</p>
          <h2 id="review-title">A little human judgment.</h2>
        </div>
        <button
          className="icon-button"
          onClick={onClose}
          disabled={saving}
          aria-label="Close review"
        >
          <X size={20} />
        </button>
      </div>
      <div className="review-transaction">
        <strong>{row.description}</strong>
        <div>
          <span>
            {shortDate(row.date)}, {row.date.slice(0, 4)} · Source row{" "}
            {row.row_number}
          </span>
          <strong>{money(row.amount_cents, currency)}</strong>
        </div>
      </div>
      <div
        className={`decision-note ${row.status === "needs_review" ? "amber" : ""}`}
      >
        <Info size={18} />
        <div>
          <strong>
            {row.status === "needs_review"
              ? "Why this needs a look"
              : "Why this category?"}
          </strong>
          <p>{row.reason}</p>
          {row.duplicate_of && (
            <p>
              Choose “Exclude duplicate / ignore” if it is repeated, or confirm
              its type and category to count it separately.
            </p>
          )}
        </div>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <div className="form-grid">
          <label>
            Transaction type
            <select
              value={kind}
              onChange={(e) => changeKind(e.target.value as Kind)}
              disabled={saving}
              required
            >
              <option value="" disabled>
                Choose a type
              </option>
              {row.amount_cents < 0 ? (
                <option value="expense">Business expense</option>
              ) : (
                <>
                  <option value="refund">Expense refund</option>
                  <option value="income">Client income</option>
                </>
              )}
              <option value="transfer">Transfer / card payment</option>
              <option value="personal">Personal transaction</option>
              <option value="excluded">Exclude duplicate / ignore</option>
            </select>
          </label>
          <label>
            Category
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={saving || !kind}
              required
            >
              <option value="" disabled>
                Choose a category
              </option>
              {categories.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <label className="full-width">
            Note <span className="optional">(optional)</span>
            <textarea
              value={note}
              maxLength={500}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add context for your future self…"
              rows={3}
              disabled={saving}
            />
          </label>
        </div>
        {error && (
          <p className="error-message" role="alert">
            {error}
          </p>
        )}
        <details className="decision-history">
          <summary>Original decision & review history</summary>
          <p>
            Original: {row.original_category || "Uncategorized"} ·{" "}
            {row.original_kind}
          </p>
          <p>{row.original_reason}</p>
          <p className="field-hint">Rule: {row.rule_id.replaceAll("_", " ")}</p>
          {row.history.map((item) => (
            <div className="history-item" key={item.id}>
              <strong>
                {item.category} · {item.kind}
              </strong>
              <span>{new Date(item.created_at).toLocaleString()}</span>
              {item.note && <p>{item.note}</p>}
            </div>
          ))}
          {!row.history.length && <p>No manual changes yet.</p>}
        </details>
        <div className="modal-actions">
          <button
            type="button"
            className="button secondary"
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </button>
          <button
            className="button primary"
            disabled={saving || !kind || !category}
          >
            {saving ? (
              <LoaderCircle size={16} className="spin" />
            ) : (
              <Check size={16} />
            )}
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
