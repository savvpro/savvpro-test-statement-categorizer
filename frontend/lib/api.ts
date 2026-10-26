export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

export type Status = "auto" | "learned" | "user" | "needs_review" | "duplicate" | "not_spending";
export type Source = "rule" | "learned" | "user" | "none";
export type CategoryKind = "spending" | "refund" | "income" | "not_spending" | "review";

export interface Transaction {
  id: number;
  statement_id: number;
  row_number: number;
  date: string;
  description: string;
  normalized_merchant: string;
  amount: number;
  currency: string;
  category: string;
  confidence: number;
  reason: string;
  needs_review: boolean;
  is_duplicate: boolean;
  source: Source;
  status: Status;
  notes: string[];
}

export interface Statement {
  id: number;
  filename: string;
  uploaded_at: string;
  row_count: number;
  warnings: string[];
  transactions: Transaction[];
}

export interface StatementListItem {
  id: number;
  filename: string;
  uploaded_at: string;
  row_count: number;
  needs_review_count: number;
}

export interface CategoryTotal {
  category: string;
  kind: CategoryKind;
  total: number;
  count: number;
}

export interface Summary {
  statement_id: number;
  totals: {
    transactions: number;
    auto_categorized: number;
    needs_review: number;
    duplicates: number;
    spending: number;
    refunds: number;
    net_spending: number;
    income: number;
    not_spending: number;
  };
  categories: CategoryTotal[];
}

export interface LearnedRule {
  id: number;
  merchant: string;
  category: string;
  created_at: string;
  times_applied: number;
}

export interface PatchResult {
  transaction: Transaction;
  learned_rule: LearnedRule | null;
  also_updated: number[];
}

export type SampleName = "bank_a" | "bank_b" | "messy";

/** Fallback when GET /api/categories fails; mirrors docs/api-contract.md. */
export const DEFAULT_CATEGORIES = [
  "Software & Subscriptions",
  "Travel",
  "Meals",
  "Office Supplies",
  "Internet & Phone",
  "Advertising",
  "Bank Fees",
  "Income",
  "Refund",
  "Transfer (not spending)",
  "Card Payment (not spending)",
  "Personal",
  "Needs Review",
];

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function detailToMessage(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  // FastAPI validation errors (422) return a list of {loc, msg}
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : null))
      .filter(Boolean);
    if (msgs.length) return msgs.join("; ");
  }
  return null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init });
  } catch {
    throw new ApiError(`Cannot reach the API at ${API_URL}. Is the backend running?`, 0);
  }
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      message = detailToMessage(body?.detail) ?? message;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(message, res.status);
  }
  if (res.status === 204) return undefined as T;
  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError("The API returned an unreadable response", res.status);
  }
}

export function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}

export const api = {
  health: () => request<{ status: string }>("/api/health"),
  categories: () => request<string[]>("/api/categories"),
  listStatements: () => request<StatementListItem[]>("/api/statements"),
  getStatement: (id: number) => request<Statement>(`/api/statements/${id}`),
  getSummary: (id: number) => request<Summary>(`/api/statements/${id}/summary`),
  uploadStatement: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Statement>("/api/statements", { method: "POST", body: form });
  },
  loadSample: (name: SampleName = "messy") =>
    request<Statement>(`/api/statements/sample?name=${encodeURIComponent(name)}`, { method: "POST" }),
  updateCategory: (transactionId: number, category: string) =>
    request<PatchResult>(`/api/transactions/${transactionId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category }),
    }),
  listRules: () => request<LearnedRule[]>("/api/rules/learned"),
  deleteRule: (id: number) => request<void>(`/api/rules/learned/${id}`, { method: "DELETE" }),
  exportUrl: (id: number) => `${API_URL}/api/statements/${id}/export`,
};
