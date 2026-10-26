import { useState } from "react";
import type { FormEvent } from "react";
import type { Category, SaveCorrection, Transaction } from "../types";
import { CategorySelect } from "./CategorySelect";

interface Props {
  txn: Transaction;
  categories: Category[];
  saving: boolean;
  onSave: SaveCorrection;
}

export function CorrectionForm({ txn, categories, saving, onSave }: Props) {
  const isReview = txn.status === "needs_review";
  const suggestions = (txn.suggestions ?? []).filter((id) => id !== "needs_review");
  // Preselect the top suggestion, but never save until the user confirms.
  const [categoryId, setCategoryId] = useState(
    isReview ? (suggestions[0] ?? "") : txn.category_id,
  );
  const [applyToSimilar, setApplyToSimilar] = useState(false);
  const selectId = `cat-${txn.id}`;
  const checkId = `similar-${txn.id}`;

  const suggestedChips = suggestions
    .map((id) => categories.find((c) => c.id === id))
    .filter((c): c is Category => c !== undefined);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!categoryId || saving) return;
    void onSave(txn.id, categoryId, applyToSimilar);
  }

  return (
    <form className="correction-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor={selectId}>Category</label>
        <CategorySelect
          id={selectId}
          categories={categories}
          value={categoryId}
          onChange={setCategoryId}
          disabled={saving}
        />
        {suggestedChips.length > 0 && (
          <div className="suggestions" role="group" aria-label="Suggested categories">
            <span className="muted small">Suggested:</span>
            {suggestedChips.map((c) => (
              <button
                key={c.id}
                type="button"
                className="chip small-chip"
                aria-pressed={categoryId === c.id}
                disabled={saving}
                onClick={() => setCategoryId(c.id)}
              >
                {c.name}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="check">
        <input
          id={checkId}
          type="checkbox"
          checked={applyToSimilar}
          onChange={(e) => setApplyToSimilar(e.target.checked)}
          disabled={saving}
        />
        <label htmlFor={checkId}>Apply to similar transactions</label>
      </div>
      <button type="submit" className="button primary" disabled={!categoryId || saving}>
        {saving ? "Saving…" : "Save"}
      </button>
    </form>
  );
}
