import type { Confidence } from '../types'

type ConfidenceBadgeProps = Readonly<{
  confidence: Confidence
}>

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  if (confidence === 'high') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-primary/10 text-primary font-mono text-label-sm uppercase">
        <span className="material-symbols-outlined text-[12px]">check_circle</span>
        HIGH
      </span>
    )
  }
  if (confidence === 'medium') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-tertiary/15 text-tertiary font-mono text-label-sm uppercase">
        <span className="material-symbols-outlined text-[12px]">info</span>
        MEDIUM
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-secondary/15 text-secondary font-mono text-label-sm uppercase">
      <span className="material-symbols-outlined text-[12px]">priority_high</span>
      {confidence === 'low' ? 'LOW' : 'UNKNOWN'}
    </span>
  )
}
