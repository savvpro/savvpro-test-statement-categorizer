import type {
  Categories,
  CurrencySummary,
  StatementDetail,
  StatementListItem,
  StatementSummary,
  Transaction,
} from '../api/client'

export const CATEGORIES: Categories = {
  categories: [
    'Software & Subscriptions',
    'Hosting & Cloud',
    'Travel',
    'Meals',
    'Personal',
    'Needs Review',
  ],
  kinds: ['expense', 'income', 'transfer', 'refund', 'fee', 'tax'],
}

export function makeTransaction(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: 1,
    row_number: 1,
    date: '2026-09-01',
    raw_description: 'ADOBE CREATIVE CLOUD SAN JOSE CA',
    merchant_key: 'ADOBE CREATIVE CLOUD SAN JOSE CA',
    amount: '-59.99',
    currency: 'USD',
    category: 'Software & Subscriptions',
    kind: 'expense',
    confidence: 0.95,
    rule_id: 'adobe',
    reason: 'Adobe subscription',
    needs_review: false,
    suggested_category: null,
    edited_by_user: false,
    ...overrides,
  }
}

export function makeReviewRow(overrides: Partial<Transaction> = {}): Transaction {
  return makeTransaction({
    id: 18,
    row_number: 18,
    raw_description: 'XYZ TRADERS 4471 RAWALPINDI',
    merchant_key: 'XYZ TRADERS RAWALPINDI',
    amount: '-3200.00',
    currency: 'PKR',
    category: 'Needs Review',
    confidence: 0,
    rule_id: null,
    reason: 'no rule matched',
    needs_review: true,
    ...overrides,
  })
}

export function makeDetail(
  transactions: Transaction[],
  overrides: Partial<StatementDetail> = {},
): StatementDetail {
  return {
    id: 1,
    filename: 'bank_a_card.csv',
    profile_name: 'bank_a_card',
    account_type: 'card',
    uploaded_at: '2026-10-26T12:34:22Z',
    skipped_count: 0,
    row_count: transactions.length,
    parse_error_count: 0,
    needs_review_count: transactions.filter((t) => t.needs_review).length,
    transactions,
    parse_errors: [],
    ...overrides,
  }
}

export function listItem(detail: StatementDetail): StatementListItem {
  const { transactions: _transactions, parse_errors: _errors, ...item } = detail
  return item
}

const none = { count: 0, total: '0.00' }

export function makeCurrency(overrides: Partial<CurrencySummary> = {}): CurrencySummary {
  return {
    expenses_by_category: [],
    expenses: none,
    personal: none,
    fees: none,
    income: none,
    refunds: none,
    tax_already_paid: none,
    transfers: { count: 0, total_out: '0.00', total_in: '0.00' },
    needs_review: { count: 0, total_out: '0.00', total_in: '0.00' },
    ...overrides,
  }
}

export function makeSummary(
  currencies: Record<string, CurrencySummary> = {},
  overrides: Partial<StatementSummary> = {},
): StatementSummary {
  return {
    statement_id: 1,
    currencies,
    needs_review_count: 0,
    parse_error_count: 0,
    ...overrides,
  }
}

export const TWO_CURRENCIES = makeSummary({
  USD: makeCurrency({
    expenses: { count: 2, total: '63.99' },
    expenses_by_category: [{ category: 'Software & Subscriptions', count: 2, total: '63.99' }],
    refunds: { count: 1, total: '59.99' },
  }),
  PKR: makeCurrency({
    expenses: { count: 1, total: '1850.00' },
    expenses_by_category: [{ category: 'Meals', count: 1, total: '1850.00' }],
    personal: { count: 1, total: '1100.00' },
    fees: { count: 1, total: '5000.00' },
    tax_already_paid: { count: 1, total: '120.00' },
    transfers: { count: 1, total_out: '0.00', total_in: '185000.00' },
    needs_review: { count: 2, total_out: '3200.00', total_in: '15000.00' },
  }),
})
