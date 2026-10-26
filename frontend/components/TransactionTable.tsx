import { CategorySelect } from "@/components/CategorySelect";
import { formatDate, formatPercent, formatSigned } from "@/lib/format";
import { NEEDS_REVIEW, type CategoryInfo, type Txn } from "@/lib/types";

interface Props {
  transactions: Txn[];
  categories: CategoryInfo[];
  pending: ReadonlySet<string>;
  updated: ReadonlySet<string>;
  onFix: (txn: Txn, category: string) => void;
}

function Confidence({ txn }: { txn: Txn }) {
  if (txn.user_fixed) {
    return <span className="text-xs text-ink-3">Set by you</span>;
  }
  const pct = formatPercent(txn.confidence);
  return (
    <span className="flex items-center gap-2 text-xs text-ink-3">
      <span aria-hidden className="h-1 w-10 overflow-hidden rounded-full bg-rule">
        <span className="block h-full bg-ink-3" style={{ width: pct }} />
      </span>
      <span className="num">
        {pct} <span className="sr-only">confident</span>
      </span>
    </span>
  );
}

export function TransactionTable({ transactions, categories, pending, updated, onFix }: Props) {
  return (
    <table className="w-full text-sm">
      <caption className="sr-only">
        Transactions with their category and the reason the app chose it
      </caption>
      <thead className="hidden md:table-header-group">
        <tr className="border-b border-rule-strong text-left text-ink-2">
          <th scope="col" className="w-28 py-2 pr-3 font-medium">
            Date
          </th>
          <th scope="col" className="py-2 pr-3 font-medium">
            Description
          </th>
          <th scope="col" className="w-36 py-2 pr-3 text-right font-medium">
            Amount
          </th>
          <th scope="col" className="w-64 py-2 pr-3 font-medium">
            Category
          </th>
          <th scope="col" className="py-2 font-medium">
            Why
          </th>
        </tr>
      </thead>
      <tbody className="block md:table-row-group">
        {transactions.map((t) => {
          const review = t.category === NEEDS_REVIEW;
          return (
            <tr
              key={t.id}
              className={`grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-2 border-b border-rule px-3 py-3 md:table-row md:px-0 ${
                review ? "bg-review-bg shadow-[inset_3px_0_0_var(--color-review-edge)]" : ""
              } ${updated.has(t.id) ? "row-updated" : ""}`}
            >
              <td className="num col-span-2 text-xs text-ink-3 md:table-cell md:py-3 md:pr-3 md:pl-3 md:text-sm md:text-ink-2">
                {formatDate(t.date)}
              </td>
              <td className="min-w-0 font-medium break-words md:table-cell md:py-3 md:pr-3">
                {t.description}
              </td>
              <td
                className={`num text-right font-medium md:table-cell md:py-3 md:pr-3 ${
                  t.amount < 0 ? "text-ink" : "text-pos"
                }`}
              >
                {formatSigned(t.amount)}
              </td>
              <td className="col-span-2 md:table-cell md:py-3 md:pr-3 md:align-top">
                <CategorySelect
                  txn={t}
                  categories={categories}
                  disabled={pending.has(t.id)}
                  onChange={(category) => onFix(t, category)}
                />
              </td>
              <td
                className={`col-span-2 md:table-cell md:py-3 md:pr-3 md:align-top ${
                  review ? "text-review-ink" : "text-ink-2"
                }`}
              >
                <p className="leading-snug">{t.reason}</p>
                <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1.5">
                  <Confidence txn={t} />
                  {review && t.suggestion && (
                    <button
                      type="button"
                      disabled={pending.has(t.id)}
                      onClick={() => onFix(t, t.suggestion as string)}
                      className="rounded border border-review-edge px-2 py-0.5 text-xs font-medium hover:bg-surface disabled:opacity-50"
                    >
                      Use “{t.suggestion}”
                    </button>
                  )}
                </div>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
