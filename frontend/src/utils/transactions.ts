import type { CategorizedTransaction } from '../types'

export function effectiveCategory(tx: CategorizedTransaction): string {
  return tx.user_category ?? tx.category
}

const NON_DEDUCTIBLE = new Set(['Transfer / Not Spending', 'Refund', 'Needs Review'])

export function isDeductible(tx: CategorizedTransaction): boolean {
  return !NON_DEDUCTIBLE.has(effectiveCategory(tx)) && tx.amount < 0
}

export function isReview(tx: CategorizedTransaction): boolean {
  return effectiveCategory(tx) === 'Needs Review'
}

export function isConfirmed(tx: CategorizedTransaction): boolean {
  return !isReview(tx)
}
