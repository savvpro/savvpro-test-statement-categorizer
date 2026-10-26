export type CategoryKind = "expense" | "non_spending" | "income" | "review";

export interface Category {
  id: string;
  name: string;
  kind: CategoryKind;
  deductible: "full" | "partial" | "none" | null;
}

export type AmountConvention = "auto" | "negative_is_spending" | "positive_is_spending";

export type TxnStatus = "categorized" | "needs_review" | "excluded" | "user_corrected";

export type Flag =
  | "refund"
  | "possible_duplicate"
  | "foreign_currency"
  | "large_amount"
  | "ambiguous_merchant"
  | "unmatched_refund";

export interface Transaction {
  id: string;
  line: number;
  date: string;
  description: string;
  merchant: string;
  amount: number;
  spend_amount: number;
  currency: string;
  category_id: string;
  category_name: string;
  kind: CategoryKind;
  status: TxnStatus;
  confidence: number;
  reasons: string[];
  flags: Flag[];
  refund_of: string | null;
  suggestions: string[];
}

export interface CategoryTotal {
  category_id: string;
  category_name: string;
  kind: CategoryKind;
  count: number;
  total: number;
}

export interface Summary {
  totals: CategoryTotal[];
  total_spending: number;
  total_refunds: number;
  net_spending: number;
  excluded_total: number;
  income_total: number;
  needs_review_count: number;
  transaction_count: number;
}

export interface RejectedRow {
  line: number;
  raw: string;
  reason: string;
}

export type SourceFormat = "csv" | "xlsx" | "pdf" | "ofx" | "camt053" | "mt940";

export interface AppConfig {
  max_upload_mb: number;
  accepted_extensions: string[];
  max_rows: number;
  max_pdf_pages: number;
}

export interface StatementResult {
  id: string;
  filename: string;
  source_format: SourceFormat;
  currency: string;
  created_at: string;
  convention: Exclude<AmountConvention, "auto">;
  transactions: Transaction[];
  rejected_rows: RejectedRow[];
  warnings: string[];
  summary: Summary;
}

export interface CorrectionResponse {
  statement: StatementResult;
  updated_count: number;
}

export type SaveCorrection = (
  txnId: string,
  categoryId: string,
  applyToSimilar: boolean,
) => Promise<void>;
