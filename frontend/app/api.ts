import { StatementItem, SummaryData, Transaction, TxnStatus, UploadResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export async function fetchStatements(): Promise<StatementItem[]> {
  try {
    const res = await fetch(`${API_BASE}/statements`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch statements");
    return await res.json();
  } catch (err) {
    console.warn("Backend unavailable, using local mock data:", err);
    return [];
  }
}

export async function uploadStatement(
  file: File,
  accountType: "credit_card" | "checking" = "credit_card"
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("account_type", accountType);

  const res = await fetch(`${API_BASE}/statements`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }

  return await res.json();
}

export async function fetchSummary(statementId: number): Promise<SummaryData | null> {
  try {
    const res = await fetch(`${API_BASE}/statements/${statementId}/summary`, {
      cache: "no-store",
    });
    if (!res.ok) throw new Error("Failed to fetch summary");
    return await res.json();
  } catch (err) {
    console.warn("Could not fetch statement summary:", err);
    return null;
  }
}

export async function fetchTransactions(
  statementId: number,
  params: {
    status?: string;
    category?: string;
    search?: string;
    limit?: number;
    offset?: number;
  } = {}
): Promise<{ items: Transaction[]; total: number }> {
  try {
    const url = new URL(`${API_BASE}/transactions`);
    url.searchParams.set("statement_id", statementId.toString());
    if (params.status) url.searchParams.set("status", params.status);
    if (params.category) url.searchParams.set("category", params.category);
    if (params.search) url.searchParams.set("q", params.search);
    if (params.limit) url.searchParams.set("page_size", params.limit.toString());
    if (params.offset) {
      const page = Math.floor(params.offset / (params.limit || 50)) + 1;
      url.searchParams.set("page", page.toString());
    }

    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch transactions");
    return await res.json();
  } catch (err) {
    console.warn("Could not fetch transactions:", err);
    return { items: [], total: 0 };
  }
}

export async function updateTransaction(
  statementId: number,
  txId: number,
  patch: {
    category?: string;
    status?: TxnStatus;
    save_rule?: boolean;
    user_note?: string;
  }
): Promise<Transaction> {
  const res = await fetch(`${API_BASE}/transactions/${txId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Update failed" }));
    throw new Error(err.detail || "Update failed");
  }

  return await res.json();
}

export function getExportUrl(statementId: number, type: "csv" | "xlsx"): string {
  return `${API_BASE}/statements/${statementId}/export/${type}`;
}
