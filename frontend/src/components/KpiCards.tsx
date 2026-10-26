import { formatMoney } from '../utils/format'

type KpiCardsProps = Readonly<{
  total: number
  deductible: number
  transfers: number
  refunds: number
  reviewCount: number
  reviewTotal: number
  deductibleSpend: number
  taxSavings: number
  onReviewClick: () => void
}>

export function KpiCards({
  total,
  deductible,
  transfers,
  refunds,
  reviewCount,
  reviewTotal,
  deductibleSpend,
  taxSavings,
  onReviewClick,
}: KpiCardsProps) {
  const reviewPct = total > 0 ? Math.round((reviewCount / total) * 100) : 0

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter-lg">
      <div className="p-space-xl rounded-xl bg-surface-container-low shadow-sm flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="font-mono text-label-sm uppercase tracking-wider text-on-surface-variant">
            Total Transactions
          </span>
          <span className="p-1.5 rounded-md bg-surface-container text-outline">
            <span className="material-symbols-outlined text-[16px]">receipt_long</span>
          </span>
        </div>
        <div className="my-space-md">
          <div className="font-mono text-financial-lg text-on-surface flex items-baseline gap-2">
            <span>{total}</span>
            <span className="font-mono text-label-md text-primary">100% Parsed</span>
          </div>
          <div className="font-geist text-body-sm text-on-surface-variant mt-1">
            {deductible} Deductible · {transfers} Transfers · {refunds} Refunds
          </div>
        </div>
        <div className="w-full bg-surface-container-highest rounded-full h-1.5 overflow-hidden">
          <div className="bg-primary h-full rounded-full w-full" />
        </div>
      </div>

      <div
        className="p-space-xl rounded-xl bg-surface-container-low flex flex-col justify-between"
        style={{ boxShadow: '0 0 0 1px rgba(245,158,11,0.35), 0 0 24px -4px rgba(245,158,11,0.12)' }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-space-xs">
            <span className="w-2 h-2 rounded-full bg-secondary animate-ping" />
            <span className="font-mono text-label-sm uppercase tracking-wider text-secondary font-semibold">
              Needs Review
            </span>
          </div>
          <span className="p-1.5 rounded-md bg-surface-container-high text-secondary">
            <span className="material-symbols-outlined text-[16px]">warning</span>
          </span>
        </div>
        <div className="my-space-md">
          <div className="font-mono text-financial-lg text-secondary flex items-baseline gap-2">
            <span>{reviewCount}</span>
            <span className="font-mono text-label-md text-secondary">Items Flagged</span>
          </div>
          <div className="flex items-center justify-between font-geist text-body-sm mt-1">
            <span className="font-mono text-financial-md text-on-surface">{formatMoney(reviewTotal)} ambiguous</span>
            <button
              type="button"
              onClick={onReviewClick}
              className="font-mono text-label-sm text-secondary underline cursor-pointer bg-transparent border-0"
            >
              Resolve now
            </button>
          </div>
        </div>
        <div className="w-full bg-surface-container-highest rounded-full h-1.5 overflow-hidden">
          <div className="bg-secondary h-full rounded-full" style={{ width: `${reviewPct}%` }} />
        </div>
      </div>

      <div className="p-space-xl rounded-xl bg-surface-container-low shadow-sm flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <span className="font-mono text-label-sm uppercase tracking-wider text-on-surface-variant">
            Est. Deductible Spend
          </span>
          <span className="p-1.5 rounded-md bg-surface-container text-primary">
            <span className="material-symbols-outlined text-[16px]">account_balance_wallet</span>
          </span>
        </div>
        <div className="my-space-md">
          <div className="font-mono text-financial-lg text-primary flex items-baseline gap-2">
            <span>{formatMoney(deductibleSpend)}</span>
            <span className="font-mono text-label-sm px-1.5 py-0.5 rounded bg-surface-container text-primary font-normal">
              Q4 YTD
            </span>
          </div>
          <div className="font-geist text-body-sm text-on-surface-variant mt-1">
            Tax savings approx.{' '}
            <span className="text-on-surface font-medium">{formatMoney(taxSavings)}</span> (30% effective rate)
          </div>
        </div>
        <div className="w-full bg-surface-container-highest rounded-full h-1.5 overflow-hidden">
          <div className="bg-primary h-full rounded-full w-[78%]" />
        </div>
      </div>
    </div>
  )
}
