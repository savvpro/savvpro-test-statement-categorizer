import type { CategorySummary } from '../types'
import { formatMoney } from '../utils/format'
import { scheduleCMeta } from '../utils/scheduleC'

type CategoryBreakdownProps = Readonly<{
  summaries: CategorySummary[]
  activeCategory: string | null
  onSelect: (category: string) => void
}>

export function CategoryBreakdown({ summaries, activeCategory, onSelect }: CategoryBreakdownProps) {
  return (
    <div className="flex flex-col gap-space-md mt-space-sm">
      <div className="flex items-center justify-between flex-wrap gap-space-sm">
        <div className="flex items-center gap-space-sm">
          <h2 className="font-geist text-headline-md text-on-surface">IRS Schedule C Category Breakdown</h2>
          <span className="font-mono text-label-sm px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant">
            {summaries.length} Groupings
          </span>
        </div>
        <span className="font-mono text-label-sm text-outline">Click a card to filter the statement</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-gutter">
        {summaries.map((s) => {
          const meta = scheduleCMeta(s.category)
          const isReview = s.category === 'Needs Review'
          const isRefund = s.category === 'Refund'
          const isTransfer = s.category === 'Transfer / Not Spending'
          const active = activeCategory === s.category

          return (
            <button
              key={s.category}
              type="button"
              onClick={() => onSelect(s.category)}
              className={`p-space-lg rounded-xl text-left transition-all cursor-pointer shadow-sm group ${
                active
                  ? 'bg-surface-container-high ring-1 ring-primary'
                  : 'bg-surface-container-low hover:bg-surface-container'
              }`}
            >
              <div
                className={`flex items-center justify-between font-mono text-label-sm ${
                  isReview ? 'text-secondary' : 'text-on-surface-variant'
                }`}
              >
                <span className="truncate">{meta.line}</span>
                <span
                  className={`p-1 rounded ${
                    isReview ? 'bg-secondary/20 text-secondary font-bold' : 'bg-surface-container-high text-on-surface'
                  }`}
                >
                  {s.count}
                </span>
              </div>
              <div
                className={`mt-2 font-geist text-body-md font-semibold truncate ${
                  isReview ? 'text-secondary' : isRefund ? 'text-primary' : 'text-on-surface'
                }`}
              >
                {isRefund ? 'Refund & Credits' : s.category}
              </div>
              <div className="mt-1 flex items-baseline justify-between gap-2">
                <span
                  className={`font-mono text-financial-md ${
                    isReview ? 'text-secondary' : isTransfer ? 'text-outline' : isRefund ? 'text-primary' : 'text-on-surface'
                  }`}
                >
                  {formatMoney(s.total)}
                </span>
                <span className="font-mono text-label-sm text-outline truncate">{meta.hint}</span>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
