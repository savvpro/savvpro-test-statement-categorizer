import type { TableFilter } from '../hooks/useStatementCategorizer'
import type { CategorizedTransaction } from '../types'
import { formatMoney, titleCaseDescription } from '../utils/format'
import { effectiveCategory, isDeductible, isReview } from '../utils/transactions'
import { ConfidenceBadge } from './ConfidenceBadge'

type TransactionTableProps = Readonly<{
  rows: CategorizedTransaction[]
  totalCount: number
  categories: string[]
  filter: TableFilter
  search: string
  confirmedCount: number
  reviewCount: number
  updatingId: string | null
  onSearch: (q: string) => void
  onFilter: (f: TableFilter) => void
  onCategoryChange: (id: string, category: string) => void
  onQuickApprove: (id: string) => void
}>

function filterBtnClass(active: boolean, warn?: boolean): string {
  const base = 'px-space-md py-1.5 rounded font-mono text-label-sm transition-all'
  if (active) return `${base} text-on-surface bg-surface-container-high font-semibold`
  if (warn) return `${base} text-secondary hover:text-on-surface flex items-center gap-1`
  return `${base} text-on-surface-variant hover:text-on-surface`
}

export function TransactionTable({
  rows,
  totalCount,
  categories,
  filter,
  search,
  confirmedCount,
  reviewCount,
  updatingId,
  onSearch,
  onFilter,
  onCategoryChange,
  onQuickApprove,
}: TransactionTableProps) {
  return (
    <div className="flex flex-col gap-space-md mt-space-md">
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-space-md p-space-md rounded-xl bg-surface-container-low">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-space-md flex-1">
          <div className="relative flex-1 min-w-[240px]">
            <span className="material-symbols-outlined absolute left-3 top-2.5 text-[18px] text-outline">search</span>
            <input
              value={search}
              onChange={(e) => onSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-lg bg-surface-container-lowest text-on-surface placeholder:text-outline font-geist text-body-sm focus:outline-none focus:ring-1 focus:ring-primary shadow-inner"
              placeholder="Filter by merchant or memo..."
              type="text"
            />
          </div>
          <div className="flex flex-wrap items-center p-1 rounded-lg bg-surface-container-lowest gap-1">
            <button type="button" className={filterBtnClass(filter === 'all')} onClick={() => onFilter('all')}>
              All ({totalCount})
            </button>
            <button type="button" className={filterBtnClass(filter === 'review', true)} onClick={() => onFilter('review')}>
              Needs Review ({reviewCount})
              <span className="w-1.5 h-1.5 rounded-full bg-secondary" />
            </button>
            <button type="button" className={filterBtnClass(filter === 'confirmed')} onClick={() => onFilter('confirmed')}>
              Confirmed ({confirmedCount})
            </button>
            <button
              type="button"
              className={filterBtnClass(filter === 'deductible')}
              onClick={() => onFilter('deductible')}
            >
              Deductible Only
            </button>
          </div>
        </div>
      </div>

      <div className="w-full overflow-x-auto rounded-xl bg-surface-container-lowest shadow-md">
        <table className="w-full text-left border-collapse min-w-[1080px]">
          <thead>
            <tr className="bg-surface-container text-on-surface-variant font-mono text-label-sm tracking-wider uppercase">
              <th className="py-3 px-space-md w-28">Date</th>
              <th className="py-3 px-space-lg w-72">Merchant & Descriptor</th>
              <th className="py-3 px-space-lg text-right w-36">Amount</th>
              <th className="py-3 px-space-lg w-56">Category (Schedule C)</th>
              <th className="py-3 px-space-md w-32">Confidence</th>
              <th className="py-3 px-space-lg">Rule Brain Logic</th>
              <th className="py-3 px-space-lg text-right w-28">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-container font-geist text-body-sm">
            {rows.map((tx) => {
              const cat = effectiveCategory(tx)
              const review = isReview(tx)
              const amountClass = tx.amount > 0 ? 'text-primary' : review ? 'text-secondary' : 'text-on-surface'

              return (
                <tr
                  key={tx.id}
                  className={`transition-colors ${review ? 'bg-secondary/5 hover:bg-secondary/10' : 'hover:bg-surface-container/60'}`}
                >
                  <td className={`py-3 px-space-md font-mono text-financial-md ${review ? 'text-secondary' : 'text-on-surface-variant'}`}>
                    {tx.date}
                  </td>
                  <td className="py-3 px-space-lg">
                    <div className="font-geist text-body-md text-on-surface font-semibold flex items-center gap-1.5">
                      {titleCaseDescription(tx.description)}
                      {review && <span className="w-1.5 h-1.5 rounded-full bg-secondary" />}
                    </div>
                    <div className="font-mono text-label-sm text-outline truncate max-w-xs">{tx.description}</div>
                  </td>
                  <td className={`py-3 px-space-lg text-right font-mono text-financial-md ${amountClass}`}>
                    {formatMoney(tx.amount)}
                  </td>
                  <td className="py-3 px-space-lg">
                    <div className="relative inline-flex">
                      <select
                        value={cat}
                        disabled={updatingId === tx.id}
                        onChange={(e) => onCategoryChange(tx.id, e.target.value)}
                        className={`appearance-none pl-2.5 pr-8 py-1 rounded font-mono text-label-sm cursor-pointer border-0 focus:ring-1 focus:ring-primary ${
                          review
                            ? 'bg-secondary/20 text-secondary'
                            : 'bg-surface-container-high text-on-surface hover:bg-surface-bright'
                        }`}
                      >
                        {categories.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                      <span className="material-symbols-outlined text-[14px] text-outline absolute right-1 top-1.5 pointer-events-none">
                        expand_more
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-space-md">
                    <ConfidenceBadge confidence={tx.confidence} />
                  </td>
                  <td className={`py-3 px-space-lg font-mono text-label-sm max-w-md ${review ? 'text-secondary' : 'text-on-surface-variant'}`}>
                    {tx.reason}
                  </td>
                  <td className="py-3 px-space-lg text-right">
                    {review ? (
                      <button
                        type="button"
                        title="Mark as Meals & Entertainment"
                        onClick={() => onQuickApprove(tx.id)}
                        className="px-2 py-1 rounded bg-surface-container-high hover:bg-primary hover:text-on-primary text-on-surface font-mono text-label-sm transition-colors"
                      >
                        Approve
                      </button>
                    ) : (
                      <span className="text-outline text-label-sm">{isDeductible(tx) ? 'Deductible' : '—'}</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-between gap-space-md p-space-md rounded-xl bg-surface-container-low font-mono text-label-sm text-on-surface-variant">
        <span>
          Showing <span className="text-financial-md text-on-surface">{rows.length}</span> of {totalCount} transactions
        </span>
        <span className="flex items-center gap-1 text-primary">
          <span className="material-symbols-outlined text-[14px]">verified</span>
          Deterministic rule engine
        </span>
      </div>
    </div>
  )
}
