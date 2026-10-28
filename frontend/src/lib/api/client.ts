import type {
  CategoryOut,
  CorrectionIn,
  CorrectionOut,
  ProblemJson,
  StatementOut,
  SummaryOut,
  TransactionOut,
  TransactionPage,
} from "./types";

export const BASE_URL = "/api";
export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;

export class AppError extends Error {
  status: number;
  existingId?: string;
  rowErrors: string[];
  constructor(message: string, status: number, existingId?: string, rowErrors: string[] = []) {
    super(message);
    this.name = "AppError";
    this.status = status;
    this.existingId = existingId;
    this.rowErrors = rowErrors;
  }
}

export function toAppError(problem: Partial<ProblemJson> & { status: number }): AppError {
  const { status } = problem;
  if (status === 413)
    return new AppError("The file is larger than 5 MB. Export a shorter date range and upload again.", 413);
  if (status === 415)
    return new AppError(
      "Only CSV, OFX or QFX files can be read. Export the statement in one of those formats.",
      415,
    );
  if (status === 422) {
    const rowErrors = (problem.errors ?? []) as { row_index?: number | null; message: string }[];
    const rows = rowErrors.map((e) =>
      e.row_index != null ? `Row ${e.row_index}: ${e.message}` : e.message,
    );
    const base = problem.detail ?? "Some rows could not be read.";
    return new AppError(`${base} Fix them in your spreadsheet, then upload again.`, 422, undefined, rows);
  }
  if (status === 409) {
    const m = problem.detail?.match(/[A-Za-z0-9-]{8,}/);
    return new AppError("You already uploaded this exact file.", 409, m?.[0]);
  }
  if (status === 404)
    return new AppError("We could not find that statement. It may have been deleted.", 404);
  return new AppError("Something went wrong on our side. Try again in a moment.", status);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, init);
  } catch {
    throw new AppError("Cannot reach the server. Check your connection and try again.", 0);
  }
  if (!res.ok) {
    let problem: Partial<ProblemJson> = {};
    try {
      problem = (await res.json()) as ProblemJson;
    } catch {
      /* non-JSON body */
    }
    throw toAppError({ ...problem, status: res.status });
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export interface TxFilters {
  status?: string;
  q?: string;
  limit?: number;
  offset?: number;
}

export const api = {
  listStatements: () => request<StatementOut[]>("/v1/statements"),
  getStatement: (id: string) => request<StatementOut>(`/v1/statements/${id}`),
  upload: (file: File, accountType: string) => {
    const body = new FormData();
    body.append("file", file);
    body.append("account_type", accountType);
    return request<StatementOut>("/v1/statements", { method: "POST", body });
  },
  listTransactions: (id: string, f: TxFilters = {}) => {
    const p = new URLSearchParams();
    if (f.status) p.set("status", f.status);
    if (f.q) p.set("q", f.q);
    p.set("limit", String(f.limit ?? 500));
    if (f.offset) p.set("offset", String(f.offset));
    return request<TransactionPage>(`/v1/statements/${id}/transactions?${p.toString()}`);
  },
  fix: (txId: string, body: CorrectionIn) =>
    request<CorrectionOut>(`/v1/transactions/${txId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  restore: (txId: string) =>
    request<TransactionOut>(`/v1/transactions/${txId}/restore-duplicate`, { method: "POST" }),
  summary: (id: string) => request<SummaryOut>(`/v1/statements/${id}/summary`),
  categories: () => request<CategoryOut[]>("/v1/categories"),
  exportUrl: (id: string) => `${BASE_URL}/v1/statements/${id}/export.csv`,
};
