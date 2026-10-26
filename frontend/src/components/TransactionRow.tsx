import { useState } from "react";
import { formatCents, formatDate, formatPercent } from "../lib/format";
import type { Category, Kind, Transaction } from "../types";

const FLAG_LABELS: Record<string, string> = {
  refund: "Refund",
  large_amount: "Unusually large",
  small_amount: "Unusually small",
  direction_mismatch: "Odd direction",
  possible_duplicate: "Possible duplicate",
  already_imported: "Already imported",
  ambiguous_merchant: "Mixed-use store",
  unknown_deposit: "Unknown deposit",
};

const KIND_GROUPS: { kind: Kind; label: string }[] = [
  { kind: "income", label: "Income" },
  { kind: "expense", label: "Deductible expenses" },
  { kind: "personal", label: "Not deductible" },
  { kind: "transfer", label: "Not income or spending" },
];

interface Props {
  tx: Transaction;
  categories: Category[];
  categoryMap: Map<string, Category>;
  busy: boolean;
  onChange: (tx: Transaction, category: string | null) => void;
}

export function TransactionRow({ tx, categories, categoryMap, busy, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const review = tx.status === "needs_review";
  const label = (id: string) => categoryMap.get(id)?.label ?? id;

  return (
    <>
      <tr className={`tx tx--${tx.status}`}>
        <td className="tx__date">{formatDate(tx.date)}</td>
        <td className="tx__desc">
          <span className="tx__merchant">{tx.merchant}</span>
          <span className="tx__raw" title={tx.description}>
            {tx.description}
          </span>
          {tx.flags.length > 0 && (
            <span className="tx__flags">
              {tx.flags.map((f) => (
                <span key={f} className={`chip chip--${f}`}>
                  {FLAG_LABELS[f] ?? f}
                </span>
              ))}
            </span>
          )}
        </td>
        <td className={`num tx__amount ${tx.amount_cents > 0 ? "is-in" : ""}`}>
          {tx.amount_cents > 0 ? "+" : ""}
          {formatCents(tx.amount_cents)}
        </td>
        <td className="tx__category">
          {review && tx.suggestions.length > 0 && (
            <div className="suggestions" aria-label="Suggestions">
              {tx.suggestions.slice(0, 3).map((s) => (
                <button
                  key={s}
                  className="btn btn--suggest"
                  disabled={busy}
                  onClick={() => onChange(tx, s)}
                >
                  {label(s)}
                </button>
              ))}
            </div>
          )}
          <select
            aria-label={`Category for ${tx.merchant}`}
            value={tx.category ?? ""}
            disabled={busy}
            onChange={(e) => onChange(tx, e.target.value || null)}
          >
            <option value="">{review ? "Choose a category…" : "Send back to review"}</option>
            {KIND_GROUPS.map((g) => (
              <optgroup key={g.kind} label={g.label}>
                {categories
                  .filter((c) => c.kind === g.kind)
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
              </optgroup>
            ))}
          </select>
        </td>
        <td className="tx__status">
          <button
            className={`badge badge--${tx.status}`}
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            title="Why was this decided?"
          >
            {tx.status === "auto" && `Auto · ${formatPercent(tx.confidence)}`}
            {tx.status === "needs_review" && "Needs review"}
            {tx.status === "reviewed" && "✓ You"}
          </button>
        </td>
      </tr>
      {open && (
        <tr className="tx-reasons">
          <td colSpan={5}>
            <ul>
              {tx.reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
            <span className="muted small">
              Decided by: {tx.source.replace("_", " ")}
              {tx.bank_category && ` · bank label "${tx.bank_category}"`}
              {tx.engine_category &&
                tx.engine_category !== tx.category &&
                ` · originally ${label(tx.engine_category)}`}
            </span>
          </td>
        </tr>
      )}
    </>
  );
}
