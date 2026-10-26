import { useState } from "react";
import { AlertTriangle, Check, Info, X } from "lucide-react";
import { api, money, title } from "./api";
import type { Transaction, Workspace } from "./types";

export default function ReviewPanel({
  row,
  data,
  onClose,
  onSaved,
}: {
  row: Transaction;
  data: Workspace;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [category, setCategory] = useState(row.category);
  const [kind, setKind] = useState(row.kind);
  const [purpose, setPurpose] = useState(row.purpose);
  const [percent, setPercent] = useState(row.business_percent);
  const [note, setNote] = useState(row.note);
  const [remember, setRemember] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  function changePurpose(value: string) {
    setPurpose(value);
    setPercent(value === "business" ? 100 : value === "mixed" ? 50 : 0);
  }
  async function save() {
    setBusy(true);
    setError("");
    try {
      await api(`/transactions/${row.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category,
          kind,
          purpose,
          business_percent: percent,
          note,
          remember,
        }),
      });
      await onSaved();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <aside className="review-panel" aria-label="Review transaction">
      <header>
        <h2>Review transaction</h2>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Close review"
        >
          <X size={19} />
        </button>
      </header>
      <div className="review-merchant">
        <div className="merchant-avatar">{row.description[0]}</div>
        <div>
          <strong>{row.description.split(" ").slice(0, 3).join(" ")}</strong>
          <small>{row.account}</small>
        </div>
        <strong className="review-amount">
          {money(row.amount_minor, row.currency)}
        </strong>
      </div>
      <p className="hint">
        {row.date} · Source row {row.source_row}
        {row.original_currency
          ? ` · Original ${money(row.original_amount_minor!, row.original_currency)}`
          : ""}
      </p>
      <label>
        Original description
        <div className="original-description">{row.description}</div>
      </label>
      <div className={row.needs_review ? "reason warning" : "reason"}>
        <AlertTriangle size={18} />
        <div>
          <strong>
            {row.needs_review
              ? "Your judgment is needed"
              : "Why this was categorized"}
          </strong>
          <p>{row.reason}</p>
        </div>
      </div>
      <div className="confidence">
        <Info size={14} /> Category confidence: {row.category_confidence}
        <br />
        Purpose: {title(row.purpose)}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <label>
          Transaction type
          <select
            aria-label="Transaction type"
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              const typeCategories: Record<string, string> = {
                transfer: "Transfer",
                card_payment: "Card payment",
                cash: "Cash withdrawal",
                income: "Freelance income",
              };
              if (typeCategories[e.target.value])
                setCategory(typeCategories[e.target.value]);
              if (["transfer", "card_payment", "cash"].includes(e.target.value))
                changePurpose("excluded");
            }}
          >
            {data.types.map((v) => (
              <option key={v} value={v}>
                {title(v)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Category
          <select
            aria-label="Category"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              if (e.target.value === "Family support" && row.amount_minor > 0) {
                setKind("expense");
                changePurpose("personal");
              }
            }}
          >
            {data.categories.map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <label>
          Purpose
          <select
            aria-label="Purpose"
            value={purpose}
            onChange={(e) => changePurpose(e.target.value)}
          >
            {data.purposes.map((v) => (
              <option key={v} value={v}>
                {title(v)}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>
            Business share <span className="muted">%</span>
          </span>
          <input
            type="number"
            min="0"
            max="100"
            step="1"
            required
            value={percent}
            disabled={purpose !== "mixed"}
            onChange={(e) => setPercent(Number(e.target.value))}
          />
        </label>
        <label>
          <span>
            Notes <span className="muted">optional</span>
          </span>
          <textarea
            rows={3}
            maxLength={1000}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Add context for your accountant…"
          />
        </label>
        {["expense", "transfer"].includes(kind) ? (
          <label className="checkbox">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
            />
            <span>
              Remember this exact description for this account
              <small>
                Applies to future imports. Existing rows stay unchanged.
              </small>
            </span>
          </label>
        ) : null}
        {row.possible_duplicate ? (
          <p className="warning reason">
            Possible overlap: both entries remain in totals. If duplicated,
            remove the overlapping statement in Statements, correct the source,
            and import again.
          </p>
        ) : null}
        {error ? (
          <div className="error" role="alert">
            {error}
          </div>
        ) : null}
        <button
          className="primary full"
          disabled={
            busy ||
            category === "Uncategorized" ||
            purpose === "unknown" ||
            kind === "unresolved"
          }
          type="submit"
        >
          <Check size={17} />
          {busy ? "Saving…" : "Save review"}
        </button>
        <p className="hint">
          Categories organize records. They do not establish tax deductibility.
        </p>
      </form>
    </aside>
  );
}
