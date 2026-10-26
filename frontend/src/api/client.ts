// Typed wrapper around the backend API. Amounts are decimal strings ("-1850.00") and are
// never turned into numbers: they are formatted for display only.

export interface Transaction {
  id: number
  row_number: number
  date: string
  raw_description: string
  merchant_key: string
  amount: string
  currency: string
  category: string
  kind: string
  confidence: number
  rule_id: string | null
  reason: string
  needs_review: boolean
  suggested_category: string | null
  edited_by_user: boolean
}

export interface ParseErrorItem {
  row_number: number
  raw_line: string
  reason: string
}

export interface StatementListItem {
  id: number
  filename: string
  profile_name: string
  account_type: 'card' | 'bank'
  uploaded_at: string
  skipped_count: number
  row_count: number
  parse_error_count: number
  needs_review_count: number
}

export interface StatementDetail extends StatementListItem {
  transactions: Transaction[]
  parse_errors: ParseErrorItem[]
}

export interface Categories {
  categories: string[]
  kinds: string[]
}

export interface CountTotal {
  count: number
  total: string
}

export interface CategoryTotal extends CountTotal {
  category: string
}

export interface TransferTotals {
  count: number
  total_out: string
  total_in: string
}

export interface UnreviewedTotals {
  count: number
  total_out: string
  total_in: string
}

export interface CurrencySummary {
  expenses_by_category: CategoryTotal[]
  expenses: CountTotal
  personal: CountTotal
  fees: CountTotal
  income: CountTotal
  refunds: CountTotal
  tax_already_paid: CountTotal
  transfers: TransferTotals
  needs_review: UnreviewedTotals
}

export interface StatementSummary {
  statement_id: number
  currencies: Record<string, CurrencySummary>
  needs_review_count: number
  parse_error_count: number
}

export interface CorrectionBody {
  category: string
  kind?: string
  remember: boolean
}

export interface CorrectionResult {
  transaction: Transaction
  reclassified_count: number
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

function formatValidationItem(item: unknown): string {
  const { loc, msg } = (item ?? {}) as { loc?: unknown[]; msg?: unknown }
  const field = Array.isArray(loc) ? loc.filter((part) => part !== 'body').join('.') : ''
  const message = typeof msg === 'string' ? msg : 'Invalid request'
  return field ? `${field}: ${message}` : message
}

/** The API's own message: `detail` is a string for our errors, a list for validation errors. */
async function readDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    const detail = (body as { detail?: unknown } | null)?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map(formatValidationItem).join('; ')
  } catch {
    // the body was not JSON; fall through to the generic message
  }
  return `Request failed (HTTP ${response.status})`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, init)
  } catch {
    throw new ApiError('Cannot reach the server. Is the backend running?', 0)
  }
  if (!response.ok) throw new ApiError(await readDetail(response), response.status)
  return (await response.json()) as T
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong'
}

export function uploadStatement(file: File): Promise<StatementDetail> {
  const form = new FormData()
  form.append('file', file)
  return request<StatementDetail>('/api/statements', { method: 'POST', body: form })
}

export function listStatements(): Promise<StatementListItem[]> {
  return request<StatementListItem[]>('/api/statements')
}

export function getStatement(id: number): Promise<StatementDetail> {
  return request<StatementDetail>(`/api/statements/${id}`)
}

export function getSummary(id: number): Promise<StatementSummary> {
  return request<StatementSummary>(`/api/statements/${id}/summary`)
}

export function exportUrl(id: number): string {
  return `${BASE}/api/statements/${id}/export`
}

export function getCategories(): Promise<Categories> {
  return request<Categories>('/api/categories')
}

export function correctTransaction(id: number, body: CorrectionBody): Promise<CorrectionResult> {
  return request<CorrectionResult>(`/api/transactions/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}
