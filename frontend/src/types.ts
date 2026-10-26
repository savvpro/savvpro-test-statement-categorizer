export type Kind =
  "expense" | "refund" | "income" | "transfer" | "personal" | "unknown";
export type Decision = {
  kind: Kind;
  category: string;
  status: string;
  strength: number;
  rule_ids: string[];
  evidence: string[];
  explanation: string;
  reason: string | null;
  engine_version: string;
};
export type Transaction = {
  id: string;
  statement_id: string;
  source_row: number;
  date: string;
  description: string;
  normalized: string;
  amount_minor: number;
  kind: Kind;
  category: string;
  reviewed: boolean;
  needs_review: boolean;
  duplicate_group: string | null;
  duplicate_status: "none" | "pending" | "kept" | "excluded";
  version: number;
  decision: Decision;
};
export type ImportOptions = {
  date_column: string;
  description_column: string;
  amount_column: string;
  debit_column: string;
  credit_column: string;
  mode: "signed" | "split";
  date_format: "iso" | "dmy" | "mdy";
  sign_convention: "negative_outgoing" | "positive_outgoing";
  currency: string;
};
export type Statement = {
  id: string;
  filename: string;
  currency: string;
  row_count: number;
  blank_rows: number;
  created_at: string;
  options: ImportOptions;
};
export type Summary = {
  totals: Record<string, number>;
  counts: Record<string, number>;
  provisional: boolean;
  reconciled: boolean;
  currency: string;
  categories: {
    category: string;
    label: string;
    expense_minor: number;
    refund_minor: number;
    net_minor: number;
    count: number;
  }[];
};
export type StatementEntry = { statement: Statement; summary: Summary };
export type CategoryData = {
  categories: Record<string, string>;
  kind_categories: Record<Kind, string[]>;
};
export type Preview = {
  headers: string[];
  rows: { source_row: number; cells: string[] }[];
  row_count: number;
  blank_rows: number;
  suggestions: Partial<ImportOptions>;
};
export type Issue = {
  row: number | null;
  field: string | null;
  message: string;
};
export type ReviewPatch = {
  action: "save" | "reset" | "duplicate";
  kind?: Kind;
  category?: string;
  duplicate_action?: "keep" | "exclude" | "reset";
  version: number;
};

export type Workspace = {
  statement: Statement;
  transactions: Transaction[];
  summary: Summary;
};
