const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

export interface Transaction {
  id: string;
  date: string | null;
  description: string;
  amount: number | null;
  category: string;
  confidence: number;
  reason: string;
  is_review: boolean;
  original_category?: string | null;
}

export interface UploadResponse {
  filename: string;
  total: number;
  transactions: Transaction[];
}

export interface SummaryItem {
  category: string;
  count: number;
  total: number;
}

export interface SummaryResponse {
  summary: SummaryItem[];
}

export async function uploadStatement(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }

  return res.json();
}

export async function overrideCategory(
  sessionId: string,
  transactionId: string,
  category: string
): Promise<Transaction> {
  const res = await fetch(
    `${BASE_URL}/transactions/${encodeURIComponent(sessionId)}/${transactionId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: transactionId, category }),
    }
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Override failed" }));
    throw new Error(err.detail || "Override failed");
  }

  return res.json();
}

export async function getSummary(sessionId: string): Promise<SummaryResponse> {
  const res = await fetch(
    `${BASE_URL}/sessions/${encodeURIComponent(sessionId)}/summary`
  );

  if (!res.ok) {
    throw new Error("Failed to load summary");
  }

  return res.json();
}

export async function getCategories(): Promise<string[]> {
  const res = await fetch(`${BASE_URL}/categories`);
  if (!res.ok) throw new Error("Failed to load categories");
  const data = await res.json();
  return data.categories;
}
