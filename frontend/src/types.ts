export type TransactionType =
  | "income"
  | "expense"
  | "refund"
  | "transfer"
  | "fee"
  | "unknown";

export type BusinessCategory =
  | "Software"
  | "Advertising"
  | "Office Supplies"
  | "Travel"
  | "Accommodation"
  | "Bank Fees"
  | "Meals & Entertainment"
  | "Client Income"
  | "Payment Processing"
  | "Internal Transfer"
  | "Cash Withdrawal"
  | "Contractor Expense"
  | "General Expense"
  | "Unknown";

export type ReviewStatus =
  | "auto"
  | "needs_review"
  | "user_confirmed"
  | "user_corrected";

export type Confidence = "high" | "medium" | "low";

export interface CategorizedTransaction {
  id: number;
  date: string;
  description: string;
  amount: string; // serialized Decimal from backend
  transaction_type: TransactionType;
  business_category: BusinessCategory;
  review_status: ReviewStatus;
  confidence: Confidence;
  explanation: string;
  rule_id: string;
  is_possible_duplicate: boolean;
  duplicate_group_id?: number | null;
  linked_transaction_id?: number | null;
}

export interface FinancialSummary {
  total_income: string;
  total_expenses: string;
  total_refunds: string;
  matched_refunds?: string;
  unmatched_refunds?: string;
  total_transfers: string;
  total_fees: string;
  net_expenses: string;
  net_operating_result: string;
  transaction_count: number;
  needs_review_count: number;
  unclassified_amount?: string;
  duplicate_count?: number;
  is_provisional?: boolean;
  category_totals: Record<string, string>;
}

export interface ParseResponse {
  transactions: CategorizedTransaction[];
  summary: FinancialSummary;
  warnings: string[];
}

export const TRANSACTION_TYPES: { value: TransactionType; label: string }[] = [
  { value: "income", label: "Income" },
  { value: "expense", label: "Expense" },
  { value: "refund", label: "Refund" },
  { value: "transfer", label: "Transfer" },
  { value: "fee", label: "Fee" },
  { value: "unknown", label: "Unknown" },
];

export const BUSINESS_CATEGORIES: BusinessCategory[] = [
  "Software",
  "Advertising",
  "Office Supplies",
  "Travel",
  "Accommodation",
  "Bank Fees",
  "Meals & Entertainment",
  "Client Income",
  "Payment Processing",
  "Internal Transfer",
  "Cash Withdrawal",
  "Contractor Expense",
  "General Expense",
  "Unknown",
];
