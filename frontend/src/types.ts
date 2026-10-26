export const expenseCategories = [
  "Software",
  "Travel",
  "Meals",
  "Office supplies",
  "Professional services",
  "Marketing",
  "Bank fees",
] as const;
export const categories = [
  ...expenseCategories,
  "Income",
  "Transfers",
  "Personal",
  "Needs Review",
] as const;
export type Category = (typeof categories)[number];
export type Kind =
  "expense" | "refund" | "income" | "transfer" | "personal" | "unknown";
export type Status = "auto" | "needs_review" | "reviewed";
export type AmountMode = "bank_signed" | "card_signed" | "debit_credit";
export type DateFormat = "iso" | "day_first" | "month_first";

export interface Transaction {
  id: string;
  source_row: number;
  date: string;
  description: string;
  amount_minor: number;
  currency: string;
  category: Category;
  kind: Kind;
  confidence: number;
  rule_id: string;
  reason: string;
  status: Status;
  review_flags: string[];
  duplicate_of: string | null;
  excluded: boolean;
  version: number;
  note: string;
  original_decision: {
    category: Category;
    kind: Kind;
    confidence: number;
    rule_id: string;
    reason: string;
    engine_version: string;
  };
}
export interface CategoryTotal {
  category: string;
  spent_minor: number;
  refund_minor: number;
  net_minor: number;
  count: number;
}
export interface Summary {
  transaction_count: number;
  review_count: number;
  auto_count: number;
  reviewed_count: number;
  excluded_count: number;
  spent_minor: number;
  refund_minor: number;
  net_expenses_minor: number;
  income_minor: number;
  transfer_in_minor: number;
  transfer_out_minor: number;
  raw_net_minor: number;
  accepted_net_minor: number;
  unresolved_net_minor: number;
  excluded_net_minor: number;
  unresolved_in_minor: number;
  unresolved_out_minor: number;
  categories: CategoryTotal[];
}
export interface StatementListItem {
  id: string;
  filename: string;
  currency: string;
  created_at: string;
  transaction_count: number;
  review_count: number;
}
export interface Statement extends StatementListItem {
  transactions: Transaction[];
  summary: Summary;
  engine_version: string;
  amount_mode: AmountMode;
  date_format: DateFormat;
}
export interface ReviewInput {
  category: Category;
  kind: Kind;
  excluded: boolean;
  note: string;
  expected_version: number;
}
export interface RowError {
  row: number;
  message: string;
}
export interface AuditEvent {
  id: string;
  created_at: string;
  note: string;
  transaction_id: string;
  previous_value: Transaction;
  new_value: Transaction;
}
