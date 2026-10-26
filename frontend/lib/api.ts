import type { FixResponse, Statement } from "./types";

const ORIGIN = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const API = `${ORIGIN}/api`;

export class ApiError extends Error {}

async function readDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    // FastAPI validation errors arrive as a list of {msg}
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  } catch {
    /* not JSON */
  }
  return `Something went wrong (HTTP ${res.status}).`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, init);
  } catch {
    throw new ApiError(
      `Can't reach the server at ${ORIGIN}. Start the backend and try again.`,
    );
  }
  if (!res.ok) throw new ApiError(await readDetail(res));
  return (await res.json()) as T;
}

export function uploadStatement(file: File, purchasesPositive: boolean): Promise<Statement> {
  const form = new FormData();
  form.append("file", file);
  const query = purchasesPositive ? "?purchases_positive=true" : "";
  return request<Statement>(`/statements${query}`, { method: "POST", body: form });
}

export function fixTransaction(
  statementId: string,
  transactionId: string,
  category: string,
): Promise<FixResponse> {
  return request<FixResponse>(`/statements/${statementId}/transactions/${transactionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category }),
  });
}

export function exportUrl(statementId: string): string {
  return `${API}/statements/${statementId}/export.csv`;
}

/** The bundled sample, fetched as a File so it takes the same upload path as a real one. */
export async function fetchSampleFile(): Promise<File> {
  let res: Response;
  try {
    res = await fetch(`${API}/sample-statement`);
  } catch {
    throw new ApiError(`Can't reach the server at ${ORIGIN}. Start the backend and try again.`);
  }
  if (!res.ok) throw new ApiError(await readDetail(res));
  return new File([await res.blob()], "driver_statement.csv", { type: "text/csv" });
}
