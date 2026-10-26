export interface Transaction {
  id: string;
  statement_id: string;
  account: string;
  date: string;
  description: string;
  amount_minor: number;
  currency: string;
  original_amount_minor: number | null;
  original_currency: string | null;
  source_row: number;
  kind: string;
  category: string;
  purpose: string;
  category_confidence: string;
  needs_review: boolean;
  reason: string;
  rule_id: string;
  rule_version: string;
  business_percent: number;
  review_status: string;
  note: string;
  possible_duplicate: boolean;
}
export interface Totals {
  business: number;
  personal: number;
  unallocated: number;
  excluded: number;
  gross_expenses: number;
  refunds: number;
  net_expenses: number;
  money_in: number;
  money_out: number;
  net_movement: number;
  income: number;
  unresolved_credits: number;
  categories: Record<string, number>;
}
export interface Statement {
  id: string;
  account: string;
  account_type: string;
  filename: string;
  row_count: number;
  period_start: string;
  period_end: string;
}
export interface Rule {
  id: string;
  account: string;
  match_text: string;
  kind: string;
  category: string;
  purpose: string;
  business_percent: number;
}
export interface Workspace {
  transactions: Transaction[];
  statements: Statement[];
  rules: Rule[];
  summary: {
    currencies: Record<string, Totals>;
    total_rows: number;
    needs_review: number;
    confirmed: number;
  };
  categories: string[];
  types: string[];
  purposes: string[];
}
export interface ImportSettings {
  account: string;
  account_type: string;
  currency: string;
  date_order: string;
  amount_direction: string;
  mapping: Record<string, string>;
}
export interface Inspection {
  headers: string[];
  rows: string[][];
  mapping: Record<string, string>;
  row_count: number;
}
export interface Preview {
  rows: Transaction[];
  valid_count: number;
  errors: { row: number; message: string }[];
  source_count: number;
  summary: Record<string, number>;
}
