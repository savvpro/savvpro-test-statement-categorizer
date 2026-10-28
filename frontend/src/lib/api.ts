import type { Category, StatementResult } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(`Cannot reach the API at ${API_URL}. Is the backend running?`);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(body?.detail ?? `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export function uploadStatement(file: File, sign: "auto" | "bank" | "card" = "auto") {
  const form = new FormData();
  form.append("file", file);
  return request<StatementResult>(`/api/statements?sign=${sign}`, { method: "POST", body: form });
}

export function fixTransaction(id: number, category: string, applyToSimilar = true, remember = true) {
  return request<StatementResult>(`/api/transactions/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category, apply_to_similar: applyToSimilar, remember }),
  });
}

export const getCategories = () => request<Category[]>("/api/categories");

export const exportUrl = (statementId: number) => `${API_URL}/api/statements/${statementId}/export.csv`;

export const getStatement = (statementId: number) => request<StatementResult>(`/api/statements/${statementId}`);
