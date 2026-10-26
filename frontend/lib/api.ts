export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Money fields arrive as strings (Pydantic Decimal). Never convert them to float for math.
export type Transaction = {
  id: number;
  date: string;
  description: string;
  normalized: string;
  amount: string;
  balance: string | null;
  usd_hint: boolean;
  category: string;
  confidence: number;
  reason: string;
  needs_review: boolean;
  flags: string[];
  user_edited: boolean;
  refund_of: number | null;
};

export type CategoryTotal = { category: string; count: number; net: string };

export type Summary = {
  categories: CategoryTotal[];
  total_income: string;
  total_spending: string;
  needs_review_count: number;
};

export type UploadResponse = { transactions: Transaction[]; skipped_rows: string[] };

// FastAPI sends {detail: string} for HTTPException and {detail: [{msg}]} for validation errors.
function detailText(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d?.msg ?? String(d)).join("; ");
  return fallback;
}

// The one place that talks to the network and turns failures into readable messages.
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new Error(`Cannot reach the API at ${API_URL}. Is the backend running?`);
  }
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) throw new Error(detailText(body, `Request failed (${res.status}).`));
  return body as T;
}

export function uploadCsv(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return request("/upload", { method: "POST", body: form });
}

export const getTransactions = () => request<Transaction[]>("/transactions");
export const getSummary = () => request<Summary>("/summary");
export const getCategories = () => request<string[]>("/categories");

export function updateCategory(id: number, category: string): Promise<Transaction[]> {
  return request(`/transactions/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category }),
  });
}
