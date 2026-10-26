export interface Transaction {
  id: string;
  date: string;
  original_date: string;
  description: string;
  normalized_description: string;
  amount: string; // Decimal serialized as string
  direction: 'expense' | 'income' | 'transfer' | 'refund' | 'other';
  category: string;
  confidence: number;
  reason: string;
  needs_review: boolean;
  user_edited: boolean;
  notes?: string | null;
  is_duplicate: boolean;
  duplicate_reason?: string | null;
}

export interface ParseIssue {
  row_number: number;
  raw_content: string;
  issue: string;
}

export interface CategorySummaryItem {
  category: string;
  count: number;
  total_amount: string;
  percentage: number;
  deductible_note?: string | null;
}

export interface SummaryResponse {
  total_transactions: number;
  total_expenses: string;
  total_income: string;
  total_refunds: string;
  total_transfers: string;
  total_needs_review_count: number;
  total_needs_review_amount: string;
  net_operating_total: string;
  category_breakdown: CategorySummaryItem[];
}

export interface StatementPreviewResponse {
  filename: string;
  total_rows: number;
  valid_rows: number;
  rejected_rows: number;
  issues: ParseIssue[];
  transactions: Transaction[];
  summary: SummaryResponse;
}

export interface CategoryInfo {
  categories: string[];
  descriptions: Record<string, string>;
}
