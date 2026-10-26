// Mirrors the backend response models (backend/app/models.py, api/schemas.py).

export type Kind =
  | "income"
  | "deductible"
  | "personal"
  | "excluded"
  | "refund"
  | "review";

export const NEEDS_REVIEW = "Needs Review";

export interface CategoryInfo {
  name: string;
  kind: Kind;
}

export interface Txn {
  id: string;
  row: number; // line number in the uploaded file
  date: string; // ISO yyyy-mm-dd
  description: string;
  amount: number; // negative = money out
  category: string;
  confidence: number; // 0..1
  reason: string;
  suggestion: string | null;
  related_category: string | null;
  user_fixed: boolean;
}

export interface RowIssue {
  row: number;
  message: string;
}

export interface CategoryTotal {
  category: string;
  kind: Kind;
  count: number;
  total: number;
}

export interface TaxSummary {
  income: number;
  deductible_expenses: number;
  refunds_netted: number;
  personal_spending: number;
  other_refunds: number;
  not_spending: number;
  estimated_profit: number;
  needs_review_count: number;
  needs_review_in: number;
  needs_review_out: number;
  complete: boolean;
}

export interface Summary {
  total_transactions: number;
  needs_review: number;
  by_category: CategoryTotal[];
  tax: TaxSummary;
}

export interface Statement {
  id: string;
  filename: string;
  currency: string;
  categories: CategoryInfo[];
  created_at: string;
  transactions: Txn[];
  skipped: RowIssue[];
  warnings: RowIssue[];
  summary: Summary;
}

export interface FixResponse {
  statement: Statement;
  updated_ids: string[];
}
