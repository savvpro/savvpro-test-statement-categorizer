export type TransactionType = "DEBIT" | "CREDIT";

export interface CategorizedTransaction {
  id: string;
  line_number: number;
  date: string;
  raw_description: string;
  normalized_description: string;
  amount: number;
  transaction_type: TransactionType;
  category: string;
  confidence: number;
  reason: string;
  needs_review: boolean;
  is_refund: boolean;
  refund_parent_id?: string | null;
  is_transfer: boolean;
  is_duplicate: boolean;
  is_personal_ambiguous: boolean;
  user_overridden: boolean;
  currency: string;
}

export interface CategoryTotal {
  category: string;
  count: number;
  total_amount: number;
  percentage_of_expenses: number;
}

export interface StatementSummary {
  total_transactions: number;
  total_income: number;
  total_expenses: number;
  total_transfers: number;
  total_refunds: number;
  needs_review_count: number;
  duplicate_count: number;
  review_progress_percent: number;
}

export interface CategorizationResponse {
  filename: string;
  transactions: CategorizedTransaction[];
  category_totals: CategoryTotal[];
  summary: StatementSummary;
}

export interface CustomRule {
  id: string;
  pattern: string;
  category: string;
  rule_type: string;
  is_active: boolean;
  notes?: string;
}
