import type { CategoryOut, StatementOut, SummaryOut, TransactionOut } from "@/lib/api/types";

export const categories: CategoryOut[] = [
  { code: "RENT", label: "Rents received", kind: "income", schedule_e_line: "3", allowed_directions: ["inflow"] },
  { code: "REPAIRS", label: "Repairs", kind: "expense", schedule_e_line: "14", allowed_directions: ["outflow"] },
  { code: "UTILITIES", label: "Utilities", kind: "expense", schedule_e_line: "17", allowed_directions: ["outflow"] },
  { code: "MORTGAGE_INTEREST", label: "Mortgage interest paid to banks", kind: "expense", schedule_e_line: "12", allowed_directions: ["outflow"] },
  { code: "PERSONAL", label: "Personal (not deductible)", kind: "non_pnl", schedule_e_line: null, allowed_directions: ["inflow", "outflow"] },
  { code: "TRANSFER", label: "Transfer between accounts", kind: "non_pnl", schedule_e_line: null, allowed_directions: ["inflow", "outflow"] },
];

export function tx(over: Partial<TransactionOut> = {}): TransactionOut {
  return {
    id: "t1",
    row_index: 1,
    posted_date: "2026-03-06",
    amount_cents: -341200,
    direction: "outflow",
    description: "HOME DEPOT #4410",
    memo: null,
    merchant_key: "home depot",
    category: null,
    brain_category: "REPAIRS",
    status: "needs_review",
    confidence: 0.55,
    reasons: ["Matched a hardware store"],
    flags: ["POSSIBLE_CAPITAL_IMPROVEMENT"],
    is_refund: false,
    duplicate_of_id: null,
    similar_count: 2,
    ...over,
  };
}

export const statement: StatementOut = {
  id: "s1",
  filename: "checking_q1_2026.csv",
  source_format: "csv",
  account_type: "checking",
  uploaded_at: "2026-04-01T00:00:00Z",
  period_start: "2026-01-01",
  period_end: "2026-03-31",
  row_count: 64,
  counts: { auto: 51, needs_review: 9, user_confirmed: 0, duplicate: 4 },
  warnings: [],
};

export const summary: SummaryOut = {
  income: { RENT: 1665000 },
  expenses: { REPAIRS: -120418, UTILITIES: -38840 },
  schedule_e: [
    { line: "3", label: "Rents received", category: "RENT", total_cents: 1665000 },
    { line: "14", label: "Repairs", category: "REPAIRS", total_cents: -120418 },
    { line: "17", label: "Utilities", category: "UTILITIES", total_cents: -38840 },
  ],
  total_income_cents: 1665000,
  total_expense_cents: -159258,
  net_cents: 1505742,
  excluded: { TRANSFER: 500000 },
  unresolved: { count: 2, total_abs_cents: 196820 },
  duplicates: { count: 4 },
};
