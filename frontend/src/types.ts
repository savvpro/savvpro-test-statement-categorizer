export type Kind =
  | "expense"
  | "refund"
  | "income"
  | "transfer"
  | "personal"
  | "excluded"
  | "credit";
export type Status = "categorized" | "needs_review" | "reviewed";
export interface Transaction {
  id: string;
  date: string;
  description: string;
  amount_cents: number;
  source_id: string;
  row_number: number;
  duplicate_of: number | null;
  category: string | null;
  kind: Kind;
  status: Status;
  reason: string;
  rule_id: string;
  original_category: string | null;
  original_kind: Kind;
  original_reason: string;
  revision: number;
  note: string;
  history: {
    id: number;
    category: string;
    kind: Kind;
    note: string;
    created_at: string;
  }[];
}
export interface StatementListItem {
  id: string;
  filename: string;
  currency: string;
  created_at: string;
  transaction_count: number;
  needs_review: number;
}
export interface Statement {
  id: string;
  filename: string;
  currency: string;
  created_at: string;
  date_from: string;
  date_to: string;
  transactions: Transaction[];
  already_imported?: boolean;
  summary: {
    transaction_count: number;
    needs_review: number;
    reviewed: number;
    net_expenses_cents: number;
    income_cents: number;
    refunds_cents: number;
    pending_outflow_cents: number;
    pending_inflow_cents: number;
    excluded_count: number;
    categories: Record<string, number>;
  };
}
export interface ImportOptions {
  date_format: string;
  currency: string;
  amount_convention: string;
}
export interface ReviewInput {
  category: string;
  kind: Exclude<Kind, "credit">;
  note: string;
  revision: number;
}
export const expenseCategories = [
  "Software",
  "Travel",
  "Marketing",
  "Fees",
  "Office",
  "Meals",
  "Other",
];
export const allCategories = [
  ...expenseCategories,
  "Client income",
  "Transfer",
  "Personal",
  "Excluded",
];
