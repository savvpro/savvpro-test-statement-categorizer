export interface Transaction {
  row_number: number;
  date: string;
  description: string;
  amount: number;
  category: string;
  transaction_type: "purchase" | "income" | "refund" | "transfer" | "unknown";
  needs_review: boolean;
  review_reason: string | null;
}

export interface InvalidRow {
  row_number: number;
  errors: string[];
  row_data: Record<string, string | string[] | null>;
}

export interface CategorizeResponse {
  transactions: Transaction[];
  invalid_rows: InvalidRow[];
  category_totals: Record<string, number>;
  total_rows: number;
}

export interface DisplayTransaction extends Transaction {
  reviewedByUser: boolean;
}
