export interface Transaction {
  id: string;
  date: string;
  description: string;
  amount: number;
  category: string;
  confidence: number;
  reason: string;
  needs_review: boolean;
  is_duplicate: boolean;
}

export interface UploadResponse {
  transactions: Transaction[];
  summary: Record<string, number>;
  warnings: string[];
}

export interface SummaryResponse {
  totals: Record<string, number>;
  needs_review_total: number;
  spending_total: number;
}

export interface TransactionUpdate {
  category: string;
}

export interface UpdateTransactionResponse {
  transaction: Transaction;
  summary: Record<string, number>;
}
