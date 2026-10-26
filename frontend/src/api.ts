export interface Statement {
  id: number
  filename: string
  created_at: string
  transaction_count: number
  duplicate_count: number
}

export interface Transaction {
  id: number
  statement_id: number
  row_number: number
  date: string
  description: string
  amount: string
  transaction_type: string
  category: string
  automatic_category: string
  manual_category: string | null
  explanation: string
  automatic_explanation: string
  needs_review: boolean
  manually_corrected: boolean
  possible_duplicate: boolean
  duplicate_confirmed: boolean
}

export interface Summary {
  currency: string
  expenses: string
  income: string
  refunds: string
  transfers: string
  transfers_in: string
  transfers_out: string
  unclassified_in: string
  unclassified_out: string
  net_movement: string
  review_count: number
  transaction_count: number
  expense_categories: Record<string, string>
}

export interface StatementDetail {
  statement: Statement
  transactions: Transaction[]
  summary: Summary
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, options)
  } catch {
    throw new Error(
      'Could not reach the server. Check that the backend is running and try again.',
    )
  }
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(
      typeof error?.detail === 'string'
        ? error.detail
        : 'The request failed. Please try again.',
    )
  }
  return response.json()
}

export function money(value: string): string {
  return `PKR ${new Intl.NumberFormat('en-PK', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value))}`
}
