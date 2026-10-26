import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  ChevronRight,
  Copy,
  Fingerprint,
  RotateCcw,
  ShieldCheck,
  X,
} from "lucide-react";
import { money, type ApiError } from "./api";
import { ErrorNotice, StatusBadge } from "./components";
import type { CategoryData, Kind, ReviewPatch, Transaction } from "./types";

type Props = {
  row: Transaction;
  currency: string;
  categories: CategoryData;
  busy: boolean;
  error: ApiError | null;
  onReload: () => void;
  onSave: (patch: ReviewPatch) => Promise<void>;
  onClose: () => void;
  onNext: () => void;
  duplicatePeers: Transaction[];
};
const labels: Record<Kind, string> = {
  expense: "Business expense",
  refund: "Expense refund",
  income: "Income",
  transfer: "Account transfer",
  personal: "Personal / non-business",
  unknown: "Unresolved",
};
export default function ReviewPanel({
  row,
  currency,
  categories,
  busy,
  error,
  onReload,
  onSave,
  onClose,
  onNext,
  duplicatePeers,
}: Props) {
  const [kind, setKind] = useState<Kind>(row.kind);
  const [category, setCategory] = useState(row.category);
  const closeButton = useRef<HTMLButtonElement>(null);
  const errorRegion = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (error) errorRegion.current?.scrollIntoView({ block: "nearest" });
  }, [error]);
  useEffect(() => {
    closeButton.current?.focus();
  }, [row.id]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, busy]);
  const allowed = categories.kind_categories[kind] || [];
  const effectiveCategory = allowed.includes(category) ? category : "";
  const availableKinds = (Object.keys(labels) as Kind[]).filter(
    (k) =>
      k !== "unknown" &&
      (k !== "expense" || row.amount_minor < 0) &&
      (!["refund", "income"].includes(k) || row.amount_minor > 0),
  );
  const excluded = row.duplicate_status === "excluded";
  return (
    <aside className="review-panel panel" aria-label="Transaction review">
      <div className="review-heading">
        <div className="eyebrow">TRANSACTION DETAIL</div>
        <button
          ref={closeButton}
          className="icon-button"
          aria-label="Close transaction details"
          onClick={onClose}
          disabled={busy}
        >
          <X size={18} />
        </button>
      </div>
      {error && (
        <div className="review-error" ref={errorRegion}>
          <ErrorNotice error={error} />
          <button className="text-button" disabled={busy} onClick={onReload}>
            Reload transaction and totals
          </button>
        </div>
      )}
      <div className="merchant-symbol">
        <Fingerprint size={27} />
      </div>
      <h2 className="merchant-title">{row.description}</h2>
      <div className="review-meta">
        {row.date} <span>·</span> Source row {row.source_row}
      </div>
      <div
        className={`review-amount ${row.amount_minor > 0 ? "positive" : ""}`}
      >
        {money(row.amount_minor, currency)}
      </div>
      <StatusBadge row={row} />
      {row.duplicate_group && (
        <div className="duplicate-box">
          <div>
            <Copy size={16} />
            <strong>
              {excluded
                ? "Excluded duplicate"
                : row.duplicate_status === "kept"
                  ? "Confirmed separate transaction"
                  : "Possible duplicate"}
            </strong>
          </div>
          <p>
            Same date, amount, and normalized description as source{" "}
            {duplicatePeers.length === 1 ? "row" : "rows"}{" "}
            {duplicatePeers.map((p) => p.source_row).join(", ")}. Identical
            purchases can be legitimate.
          </p>
          <div className="button-row">
            {row.duplicate_status === "pending" ? (
              <>
                <button
                  className="button secondary compact"
                  disabled={busy}
                  onClick={() =>
                    void onSave({
                      action: "duplicate",
                      duplicate_action: "keep",
                      version: row.version,
                    })
                  }
                >
                  Keep this transaction
                </button>
                <button
                  className="text-button danger"
                  disabled={busy}
                  onClick={() =>
                    void onSave({
                      action: "duplicate",
                      duplicate_action: "exclude",
                      version: row.version,
                    })
                  }
                >
                  Exclude duplicate
                </button>
              </>
            ) : (
              <button
                className="text-button"
                disabled={busy}
                onClick={() =>
                  void onSave({
                    action: "duplicate",
                    duplicate_action: "reset",
                    version: row.version,
                  })
                }
              >
                <RotateCcw size={14} /> Undo duplicate decision
              </button>
            )}
          </div>
        </div>
      )}
      <section className="decision-section">
        <h3>
          <ShieldCheck size={16} /> Why this decision?
        </h3>
        <p>
          {row.reviewed
            ? "You confirmed this classification. The original engine decision is preserved below."
            : row.decision.explanation}
        </p>
        {row.reviewed && (
          <p className="muted">Original: {row.decision.explanation}</p>
        )}
        {row.decision.evidence.length > 0 && (
          <ul className="evidence-list">
            {row.decision.evidence.map((e, i) => (
              <li key={i}>
                <Check size={13} />
                {e}
              </li>
            ))}
          </ul>
        )}
        <details>
          <summary>
            Inspect decision trace <ChevronRight size={13} />
          </summary>
          <dl className="trace">
            <dt>Engine</dt>
            <dd>v{row.decision.engine_version}</dd>
            <dt>Rule IDs</dt>
            <dd>{row.decision.rule_ids.join(", ") || "No rule matched"}</dd>
            <dt>Normalized text</dt>
            <dd>{row.normalized}</dd>
            <dt>Evidence strength</dt>
            <dd>{row.decision.strength}/100 · heuristic, not a probability</dd>
            <dt>Review reason</dt>
            <dd>
              {row.decision.reason?.replaceAll("_", " ") ||
                "Specific evidence; no conflict"}
            </dd>
          </dl>
        </details>
      </section>
      {!excluded && (
        <form
          className="review-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (effectiveCategory && kind !== "unknown")
              void onSave({
                action: "save",
                kind,
                category: effectiveCategory,
                version: row.version,
              });
          }}
        >
          <h3>
            {row.reviewed ? "Your classification" : "Confirm the purpose"}
          </h3>
          <label className="field">
            Transaction kind
            <select
              aria-label="Transaction kind"
              value={kind}
              onChange={(e) => {
                const next = e.target.value as Kind;
                setKind(next);
                const values = categories.kind_categories[next];
                setCategory(values.length === 1 ? values[0] : "");
              }}
              disabled={busy}
            >
              {kind === "unknown" && (
                <option value="unknown" disabled>
                  Choose a transaction kind
                </option>
              )}
              {availableKinds.map((k) => (
                <option key={k} value={k}>
                  {labels[k]}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Category
            <select
              aria-label="Category"
              required
              value={effectiveCategory}
              onChange={(e) => setCategory(e.target.value)}
              disabled={busy}
            >
              <option value="">Choose a category</option>
              {allowed.map((c) => (
                <option value={c} key={c}>
                  {categories.categories[c]}
                </option>
              ))}
            </select>
          </label>
          <p className="field-hint">
            This changes the classification, never the original amount.
          </p>
          <button
            className="button primary wide"
            disabled={busy || !effectiveCategory || kind === "unknown"}
            type="submit"
          >
            <Check size={16} />
            {busy ? "Saving…" : "Save classification"}
          </button>
          {row.reviewed && (
            <button
              type="button"
              className="text-button centered"
              disabled={busy}
              onClick={() =>
                void onSave({ action: "reset", version: row.version })
              }
            >
              <RotateCcw size={14} /> Reset to engine decision
            </button>
          )}
        </form>
      )}
      <button
        className="next-review text-button"
        onClick={onNext}
        disabled={busy}
      >
        Next transaction needing review <ArrowRight size={15} />
      </button>
    </aside>
  );
}
