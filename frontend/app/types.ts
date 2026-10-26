export type TxnStatus = "auto" | "suggested" | "needs_review" | "user_confirmed";

export interface Transaction {
  id: number;
  statement_id: number;
  row_index: number;
  posted_date: string;
  raw_description: string;
  merchant_key: string;
  amount_cents: number;
  currency: string;
  category: string;
  confidence: number;
  status: TxnStatus;
  reason: string;
  rule_id?: number | null;
  flags: string[];
  deductible_pct: number;
  amount_dollars: string;
}

export interface CategoryTotal {
  category: string;
  label: string;
  schedule_c_line: string;
  cat_type: "income" | "expense" | "excluded" | "review";
  total_cents: number;
  deductible_cents: number;
  deductible_pct: number;
  count: number;
}

export interface StatusCounts {
  total: number;
  auto: number;
  suggested: number;
  needs_review: number;
  excluded: number;
}

export interface SummaryData {
  statement_id?: number;
  totals: CategoryTotal[];
  total_income_cents: number;
  total_expense_cents: number;
  total_deductible_cents: number;
  total_excluded_cents: number;
  net_cents: number;
  status_counts: StatusCounts;
  reconciles: boolean;
  reconciliation_note?: string;
}

export interface StatementItem {
  id: number;
  filename: string;
  account_type: "credit_card" | "checking";
  account_label: string;
  period_start?: string;
  period_end?: string;
  uploaded_at: string;
  row_count: number;
}

export interface ModalTransaction {
  id: number;
  description: string;
  category: string;
  amount: string;
  date: string;
  isPositive?: boolean;
  status?: string;
  rawTx?: Transaction;
}

export interface UploadResponse {
  statement: StatementItem;
  counts: Record<string, number>;
}

