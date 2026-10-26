export type Kind = "income" | "expense" | "personal" | "transfer";
export type Status = "auto" | "needs_review" | "reviewed";
export type SignConvention = "auto" | "negative_is_spending" | "positive_is_spending";

export interface Category {
  id: string;
  label: string;
  kind: Kind;
  schedule_c_line: string | null;
  description: string;
}

export interface Transaction {
  id: number;
  line: number;
  date: string;
  description: string;
  merchant: string;
  /** Signed: positive = money in, negative = money out. */
  amount_cents: number;
  direction: "in" | "out";
  bank_category: string | null;
  category: string | null;
  status: Status;
  confidence: number;
  source: string;
  reasons: string[];
  suggestions: string[];
  flags: string[];
  engine_category: string | null;
}

export interface CategoryTotal {
  category: string;
  label: string;
  kind: Kind;
  schedule_c_line: string | null;
  total_cents: number;
  count: number;
  refund_cents: number;
}

export interface Summary {
  income_cents: number;
  deductible_expenses_cents: number;
  net_profit_cents: number;
  personal_cents: number;
  transfers_in_cents: number;
  transfers_out_cents: number;
  needs_review_count: number;
  needs_review_cents: number;
  auto_count: number;
  reviewed_count: number;
  categories: CategoryTotal[];
}

export interface StatementListItem {
  id: number;
  filename: string;
  uploaded_at: string;
  transaction_count: number;
  needs_review_count: number;
  period_start: string | null;
  period_end: string | null;
}

export interface SkippedRow {
  line: number;
  reason: string;
  content: string;
}

export interface Statement extends StatementListItem {
  file_format: string;
  sign_convention: SignConvention;
  warnings: string[];
  skipped: SkippedRow[];
  transactions: Transaction[];
  summary: Summary;
}

export interface Rule {
  merchant_key: string;
  direction: "in" | "out";
  category: string;
  example: string;
  updated_at: string;
}

export interface Sample {
  name: string;
  title: string;
  description: string;
}
