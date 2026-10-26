export interface Account {
  id: string;
  name: string;
  type: "checking" | "credit_card";
  institution: string;
  mask: string;
}

export interface Statement {
  id: string;
  account_id: string;
  filename: string;
  format?: string;
  period_start: string | null;
  period_end: string | null;
  row_count: number;
  skipped_rows: { line: number; reason: string }[];
  warnings?: string[];
  needs_review_count?: number;
  created_at: string;
}

export interface Transaction {
  id: string;
  statement_id: string;
  account_id: string;
  posted_date: string;
  description_raw: string;
  merchant: string;
  amount_cents: number;
  kind: string;
  category_id: string | null;
  status: "auto" | "needs_review" | "confirmed";
  confidence: number;
  reasons: string[];
  review_reason: string | null;
  fingerprint: string;
  linked_txn_id?: string | null;
  note: string | null;
}

export interface Category {
  id: string;
  name: string;
  group: "income" | "expense" | "non_pl";
  schedule_c_line: string | null;
  deductible_pct: number | null;
  color: string;
  icon: string;
  description?: string;
  is_system?: boolean;
}

export interface Rule {
  id: string;
  match_type: "merchant_exact" | "contains" | "regex";
  pattern: string;
  category_id: string | null;
  kind: string | null;
  amount_min: number | null;
  amount_max: number | null;
  priority: number;
  enabled: boolean;
  hit_count: number;
  source: "user" | "correction";
  created_at: string;
}

export interface CategoryBreakdown {
  slug: string;
  name: string;
  group: string;
  total_cents: number;
  color: string;
}

export interface MonthlyTrend {
  month: string;
  income: number;
  expenses: number;
}

export interface RecentImport {
  id: string;
  filename: string;
  row_count: number;
  created_at: string;
}

export interface DashboardData {
  income_cents: number;
  total_expenses_cents: number;
  deductible_expenses_cents: number;
  net_profit_cents: number;
  needs_review_count: number;
  category_breakdown: CategoryBreakdown[];
  monthly_trend: MonthlyTrend[];
  recent_imports: RecentImport[];
}

export interface ImportDraft {
  draft_id: string;
  filename: string;
  fmt: string;
  detected_mapping: Record<string, number>;
  preview_rows: Record<string, unknown>[];
  warnings: string[];
}

export interface ReportCategory {
  slug: string;
  name: string;
  group: "income" | "expense" | "non_pl";
  total_cents: number;
  deductible_cents: number;
  deductible_pct: number;
}

export interface ReportLine {
  line: string;
  categories: ReportCategory[];
  total_cents: number;
  deductible_cents: number;
}

export interface ReportSummary {
  year: number | null;
  schedule_c_lines: ReportLine[];
  non_pl_summary: { count: number; total_cents: number };
}

export interface TransactionFilters {
  status?: string;
  category?: string;
  kind?: string;
  search?: string;
  account?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  limit?: number;
}

export interface PaginatedTransactions {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
}
