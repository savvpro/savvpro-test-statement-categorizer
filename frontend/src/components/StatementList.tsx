import { formatDate } from "../lib/format";
import type { StatementListItem } from "../types";

interface Props {
  statements: StatementListItem[];
  activeId: number | null;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
}

export function StatementList({ statements, activeId, onSelect, onDelete }: Props) {
  if (statements.length === 0) return null;
  return (
    <section className="panel" aria-labelledby="statements-title">
      <h2 id="statements-title">Your statements</h2>
      <ul className="statement-list">
        {statements.map((s) => (
          <li key={s.id} className={s.id === activeId ? "is-active" : undefined}>
            <button className="statement-list__open" onClick={() => onSelect(s.id)}>
              <span className="statement-list__name">{s.filename}</span>
              <span className="muted small">
                {s.period_start && s.period_end
                  ? `${formatDate(s.period_start)} – ${formatDate(s.period_end)}`
                  : "No transactions"}
                {" · "}
                {s.transaction_count} rows
              </span>
              {s.needs_review_count > 0 ? (
                <span className="pill pill--warn">{s.needs_review_count} to review</span>
              ) : (
                <span className="pill pill--ok">All sorted</span>
              )}
            </button>
            <button
              className="icon-btn"
              aria-label={`Delete ${s.filename}`}
              title="Delete statement"
              onClick={() => {
                if (window.confirm(`Delete ${s.filename}? This cannot be undone.`)) onDelete(s.id);
              }}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
