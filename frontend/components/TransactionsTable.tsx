import type { Transaction } from "@/lib/api";
import { categoryClass, formatSignedPkr, isDebit } from "@/lib/format";

type Props = {
  rows: Transaction[];
  byId: Map<number, Transaction>;
  categories: string[];
  savingId: number | null;
  rowErrors: Record<number, string>;
  onEdit: (id: number, category: string) => void;
};

export function TransactionsTable({ rows, byId, categories, savingId, rowErrors, onEdit }: Props) {
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Description</th>
            <th scope="col" className="num">Amount</th>
            <th scope="col">Category</th>
            <th scope="col">Confidence</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => {
            const refunded = t.refund_of !== null ? byId.get(t.refund_of) : undefined;
            return (
              <tr key={t.id} className={t.needs_review ? "review" : undefined}>
                <td className="nowrap muted">{t.date}</td>
                <td className="desc" title={t.reason}>
                  <span>{t.description}</span>
                  <small className="muted">{t.reason}</small>
                </td>
                <td className={`num nowrap ${isDebit(t.amount) ? "debit" : "credit"}`}>{formatSignedPkr(t.amount)}</td>
                <td className={categoryClass(t.category)}>
                  <select
                    aria-label={`Category for ${t.description}`}
                    className="chip chip-select"
                    value={t.category}
                    disabled={savingId === t.id}
                    onChange={(e) => onEdit(t.id, e.target.value)}
                  >
                    {t.needs_review && <option value={t.category} disabled>{t.category}</option>}
                    {categories.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                  {rowErrors[t.id] && <div className="error small" role="alert">{rowErrors[t.id]}</div>}
                </td>
                <td>
                  <span className="conf" title={`Confidence ${t.confidence.toFixed(2)}`}>
                    <span className="conf-track" aria-hidden="true">
                      <span className="conf-fill" style={{ width: `${Math.round(t.confidence * 100)}%` }} />
                    </span>
                    <span className="num">{Math.round(t.confidence * 100)}%</span>
                  </span>
                </td>
                <td>
                  <div className="badges">
                    {t.needs_review && <span className="badge b-review">Needs Review</span>}
                    {t.user_edited && <span className="badge b-edited">Edited by you</span>}
                    {t.flags.includes("duplicate") && <span className="badge b-warn">Duplicate</span>}
                    {t.flags.includes("reversal") && <span className="badge b-warn">Reversal</span>}
                    {t.flags.includes("transfer") && <span className="badge b-info">Transfer</span>}
                    {t.refund_of !== null && (
                      <span className="badge b-info">
                        Refund of #{t.refund_of}{refunded ? ` (${refunded.description})` : ""}
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
