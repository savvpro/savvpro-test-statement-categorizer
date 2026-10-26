import type { Money } from './api/types'

const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })

/** Display only. Amounts arrive as exact decimal strings and are never used for arithmetic. */
export function formatMoney(amount: Money): string {
  const value = Number(amount)
  return Number.isFinite(value) ? usd.format(value) : amount
}

export function amountTone(amount: Money): 'in' | 'out' | 'zero' {
  if (amount.startsWith('-')) return 'out'
  return /[1-9]/.test(amount) ? 'in' : 'zero'
}

const day = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })

/** "2026-01-03" -> "Jan 3, 2026". Parsed as UTC so the day never shifts with the local zone. */
export function formatDate(iso: string): string {
  const date = new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso)
  return Number.isNaN(date.getTime()) ? iso : day.format(date)
}

export type ConfidenceLevel = 'high' | 'med' | 'low'

export function confidenceLevel(confidence: number): ConfidenceLevel {
  if (confidence >= 0.9) return 'high'
  if (confidence >= 0.8) return 'med'
  return 'low'
}

export const SAMPLES = [
  { name: 'checking_simple.csv', label: 'Checking (CSV)', accountType: 'checking' },
  { name: 'credit_card.csv', label: 'Credit card (CSV)', accountType: 'credit_card' },
  { name: 'bank_messy.csv', label: 'Messy bank export', accountType: 'checking' },
  { name: 'credit_card.xlsx', label: 'Credit card (Excel)', accountType: 'credit_card' },
] as const
