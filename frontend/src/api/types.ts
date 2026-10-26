// Mirrors backend/app/schemas. Money is always a string like "-45.00"; never parse it for math.
export type Money = string

export type AccountType = 'checking' | 'credit_card'
export type TxnStatus = 'auto' | 'needs_review' | 'user_confirmed'
export type CategoryKind = 'expense' | 'income' | 'non_operating' | 'review'

export interface Category {
  id: string
  label: string
  kind: CategoryKind
  schedule_c_line: string | null
  deductible_pct: number
  description: string
}

export interface Transaction {
  id: number
  statement_id: number
  row_index: number
  date: string
  description_raw: string
  merchant_key: string
  amount: Money
  category_id: string
  suggested_category_id: string | null
  confidence: number
  status: TxnStatus
  reasons: string[]
  rule_id: string | null
  flags: string[]
  is_pending: boolean
  linked_transaction_id: number | null
  updated_at: string
}

export interface Statement {
  id: number
  filename: string
  account_type: AccountType
  uploaded_at: string
  row_count: number
  parse_errors: RowError[]
}

export interface RowError {
  line_no: number
  reason: string
  raw: Record<string, string>
}

export interface DetectedFormat {
  file_type: string
  encoding: string | null
  delimiter: string | null
  header_line: number
  column_map: Record<string, string>
  date_order: string
  sign_convention: string
  sign_reason: string
}

export interface StatementDetail extends Statement {
  warnings: string[]
  detected_format: DetectedFormat
  review_count: number
}

export interface UploadResult extends StatementDetail {
  transactions: Transaction[]
}

export interface TransactionUpdateResult {
  transaction: Transaction
  updated_count: number
}

export interface CategoryTotal {
  category_id: string
  label: string
  kind: CategoryKind
  schedule_c_line: string | null
  count: number
  total: Money
  deductible: Money
}

export interface Summary {
  statement_id: number
  income: Money
  expenses: Money
  net: Money
  estimated_deductible: Money
  categories: CategoryTotal[]
  non_operating: CategoryTotal[]
  unlinked_refunds: Money
  unlinked_refund_count: number
  needs_review_count: number
  needs_review_amount: Money
  pending_count: number
  pending_amount: Money
}

export interface MerchantRule {
  id: number
  merchant_key: string
  category_id: string
  source: string
  hits: number
  created_at: string
}

export interface ErrorBody {
  detail: string
  code?: string
  statement_id?: number
}
