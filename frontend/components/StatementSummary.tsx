import { formatMoney, formatSigned, plural } from "@/lib/format";
import type { Statement } from "@/lib/types";
import { KIND_DOT } from "@/lib/ui";

interface FigureProps {
  label: string;
  value: string;
  note?: string;
  strong?: boolean;
}

function Figure({ label, value, note, strong }: FigureProps) {
  return (
    <div className="min-w-0 py-4 sm:px-5 sm:first:pl-0">
      <dt className="text-sm text-ink-2">{label}</dt>
      <dd
        className={`num mt-1 break-words ${
          strong ? "text-3xl font-semibold" : "text-2xl font-medium"
        }`}
      >
        {value}
      </dd>
      {note && <p className="mt-1 text-xs leading-snug text-ink-3">{note}</p>}
    </div>
  );
}

interface Props {
  statement: Statement;
  onReview: () => void;
}

export function StatementSummary({ statement, onReview }: Props) {
  const { tax, by_category: rows } = statement.summary;
  const unresolved = tax.needs_review_count;

  return (
    <section aria-labelledby="summary-heading">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 id="summary-heading" className="text-lg font-semibold">
          Tax-time totals
        </h2>
        <p className="text-sm text-ink-2">All amounts in {statement.currency}</p>
      </div>

      <dl className="mt-2 grid divide-y divide-rule border-y border-rule sm:grid-cols-2 sm:divide-x sm:divide-y-0 lg:grid-cols-4">
        <Figure label="Income" value={formatMoney(tax.income)} note="Platform payouts" />
        <Figure
          label="Business expenses"
          value={formatMoney(tax.deductible_expenses)}
          note={
            tax.refunds_netted > 0
              ? `After subtracting ${formatMoney(tax.refunds_netted)} of refunds`
              : "Fuel, repairs, tolls, phone, platform fees"
          }
        />
        <Figure
          label="Personal spending"
          value={formatMoney(tax.personal_spending)}
          note="Not deductible"
        />
        <Figure
          label="Estimated profit"
          value={formatSigned(tax.estimated_profit).replace(/^\+/, "")}
          note="Income minus business expenses. An estimate, not tax advice."
          strong
        />
      </dl>

      {unresolved > 0 ? (
        <p
          className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-md border border-review-edge bg-review-bg px-4 py-3 text-sm text-review-ink"
          role="note"
        >
          <span>
            <strong className="font-semibold">{plural(unresolved, "row")} not counted yet.</strong>{" "}
            {formatMoney(tax.needs_review_in)} in and {formatMoney(tax.needs_review_out)} out are
            waiting on your review, so these totals will change.
          </span>
          <button
            type="button"
            onClick={onReview}
            className="font-semibold underline underline-offset-2 hover:no-underline"
          >
            Review them
          </button>
        </p>
      ) : (
        <p className="mt-4 text-sm text-pos" role="note">
          Every row is categorized. These totals are final for this file.
        </p>
      )}

      {(tax.other_refunds > 0 || tax.not_spending !== 0) && (
        <ul className="mt-3 space-y-1 text-xs text-ink-3">
          {tax.other_refunds > 0 && (
            <li>
              {formatMoney(tax.other_refunds)} of refunds could not be tied to a business expense.
              They are shown separately and are not counted as income.
            </li>
          )}
          {tax.not_spending !== 0 && (
            <li>
              Transfers and card payments ({formatSigned(tax.not_spending)}) are left out of
              spending.
            </li>
          )}
        </ul>
      )}

      <h3 className="mt-8 text-sm font-semibold uppercase tracking-wide text-ink-2">
        By category
      </h3>
      <table className="mt-2 w-full text-sm">
        <caption className="sr-only">Transactions and totals for each category</caption>
        <thead>
          <tr className="border-b border-rule-strong text-left text-ink-2">
            <th scope="col" className="py-2 pr-3 font-medium">
              Category
            </th>
            <th scope="col" className="py-2 pr-3 text-right font-medium">
              Rows
            </th>
            <th scope="col" className="py-2 text-right font-medium">
              Total
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.category} className="border-b border-rule">
              <th scope="row" className="py-2 pr-3 text-left font-normal">
                <span className="flex items-center gap-2">
                  <span aria-hidden className={`size-2.5 shrink-0 rounded-full ${KIND_DOT[row.kind]}`} />
                  {row.category}
                </span>
              </th>
              <td className="num py-2 pr-3 text-right text-ink-2">{row.count}</td>
              <td className="num py-2 text-right">{formatSigned(row.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
