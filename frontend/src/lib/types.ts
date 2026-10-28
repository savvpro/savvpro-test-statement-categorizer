export type Kind = "income" | "expense" | "refund" | "not_spending" | "review";

export interface Category {
  name: string;
  kind: Kind;
  deductible: boolean;
}

export interface Transaction {
  id: number;
  row: number;
  date: string;
  description: string;
  merchant: string;
  amount: string;
  category: string;
  confidence: number;
  reason: string;
  rule: string;
  suggestion: string | null;
  pending: boolean;
  refund_of: string | null;
}

export interface CategoryTotal {
  category: string;
  kind: Kind;
  deductible: boolean;
  total: string;
  count: number;
}

export interface Summary {
  income: string;
  deductible_expenses: string;
  personal_spending: string;
  not_spending: string;
  unlinked_refunds: string;
  needs_review: number;
  transactions: number;
  by_category: CategoryTotal[];
}

export interface StatementMeta {
  id: number;
  filename: string;
  uploaded_at: string;
  sign_mode: "bank" | "card";
  skipped: { row: number; reason: string }[];
}

export interface StatementResult {
  statement: StatementMeta;
  transactions: Transaction[];
  summary: Summary;
}

export const NEEDS_REVIEW = "Needs Review";
