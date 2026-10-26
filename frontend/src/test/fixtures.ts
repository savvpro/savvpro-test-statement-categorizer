import { vi } from 'vitest'
import type { Category, StatementDetail, Summary, Transaction } from '../api/types'

export const categories: Category[] = [
  { id: 'software_subscriptions', label: 'Software & Subscriptions', kind: 'expense', schedule_c_line: 'Line 18 - Office expense', deductible_pct: 100, description: 'Tools' },
  { id: 'meals', label: 'Business Meals', kind: 'expense', schedule_c_line: 'Line 24b - Deductible meals', deductible_pct: 50, description: 'Meals' },
  { id: 'client_income', label: 'Client Income', kind: 'income', schedule_c_line: 'Line 1 - Gross receipts', deductible_pct: 0, description: 'Income' },
  { id: 'personal', label: 'Personal', kind: 'non_operating', schedule_c_line: null, deductible_pct: 0, description: 'Personal' },
  { id: 'needs_review', label: 'Needs Review', kind: 'review', schedule_c_line: null, deductible_pct: 0, description: 'Review' },
]

export function txn(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: 1,
    statement_id: 7,
    row_index: 0,
    date: '2026-01-03',
    description_raw: 'ADOBE CREATIVE CLOUD',
    merchant_key: 'ADOBE CREATIVE CLOUD',
    amount: '-59.99',
    category_id: 'software_subscriptions',
    suggested_category_id: null,
    confidence: 0.92,
    status: 'auto',
    reasons: ['known merchant ADOBE'],
    rule_id: 'merchant:ADOBE',
    flags: [],
    is_pending: false,
    linked_transaction_id: null,
    updated_at: '2026-01-10T00:00:00Z',
    ...overrides,
  }
}

export const cafe = txn({
  id: 2,
  row_index: 1,
  description_raw: 'SQ *JOES CAFE 9921',
  merchant_key: 'JOES CAFE',
  amount: '-8.75',
  category_id: 'needs_review',
  suggested_category_id: 'meals',
  confidence: 0.6,
  status: 'needs_review',
  reasons: ['low confidence: best guess meals (keyword)'],
  rule_id: null,
})
export const deposit = txn({
  id: 3,
  row_index: 2,
  description_raw: 'ACH DEPOSIT HARBOR & PINE CO',
  merchant_key: 'HARBOR & PINE CO',
  amount: '2500.00',
  category_id: 'client_income',
  confidence: 0.95,
})

export const detail: StatementDetail = {
  id: 7,
  filename: 'credit_card.csv',
  account_type: 'credit_card',
  uploaded_at: '2026-01-10T12:00:00Z',
  row_count: 3,
  parse_errors: [{ line_no: 9, reason: 'invalid date "13/45/2026"', raw: {} }],
  warnings: ['line 12: skipped summary row "Total"'],
  detected_format: {
    file_type: 'csv',
    encoding: 'utf-8',
    delimiter: ',',
    header_line: 1,
    column_map: { date: 'Date', description: 'Description', amount: 'Amount' },
    date_order: 'month_first',
    sign_convention: 'charges_positive',
    sign_reason: 'most amounts are positive on a card statement',
  },
  review_count: 1,
}

export const summary: Summary = {
  statement_id: 7,
  income: '2500.00',
  expenses: '59.99',
  net: '2440.01',
  estimated_deductible: '59.99',
  categories: [
    { category_id: 'client_income', label: 'Client Income', kind: 'income', schedule_c_line: 'Line 1 - Gross receipts', count: 1, total: '2500.00', deductible: '0.00' },
    { category_id: 'software_subscriptions', label: 'Software & Subscriptions', kind: 'expense', schedule_c_line: 'Line 18 - Office expense', count: 1, total: '-59.99', deductible: '59.99' },
  ],
  non_operating: [],
  unlinked_refunds: '0.00',
  unlinked_refund_count: 0,
  needs_review_count: 1,
  needs_review_amount: '8.75',
  pending_count: 0,
  pending_amount: '0.00',
}

type Handler = (init: RequestInit | undefined, url: URL) => unknown | Response
export type Routes = Record<string, Handler>

const jsonResponse = (body: unknown, status = 200) =>
  new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

export const errorResponse = (status: number, detail: string, extra: object = {}) =>
  jsonResponse({ detail, ...extra }, status)

/** Mock fetch with "METHOD /path" -> handler. Unmatched requests fail the test loudly. */
export function mockFetch(routes: Routes) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost')
    const key = `${init?.method ?? 'GET'} ${url.pathname}`
    const handler = routes[key]
    if (!handler) throw new Error(`unexpected request ${key}`)
    const result = handler(init, url)
    return result instanceof Response ? result : jsonResponse(result)
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

export function baseRoutes(): Routes {
  return {
    'GET /api/categories': () => categories,
    'GET /api/statements': () => [],
  }
}
