import type {
  AmountConvention,
  AppConfig,
  Category,
  CorrectionResponse,
  StatementResult,
} from "../types";

export const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  /** Seconds from a Retry-After header, when the server sent one. */
  retryAfter: number | null = null;

  constructor(message: string, status: number, code: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function errorFromBody(status: number, body: unknown): ApiError {
  const fallback = `Request failed (HTTP ${status})`;
  const detail =
    body && typeof body === "object" ? (body as { detail?: unknown }).detail : undefined;

  if (typeof detail === "string" && detail) {
    return new ApiError(detail, status);
  }
  if (detail && typeof detail === "object") {
    const { code, message } = detail as { code?: unknown; message?: unknown };
    return new ApiError(
      typeof message === "string" && message ? message : fallback,
      status,
      typeof code === "string" ? code : null,
    );
  }
  if (Array.isArray(detail) && detail.length > 0) {
    // FastAPI validation errors come back as a list of {msg, ...}.
    const msgs = detail
      .map((d) => (d && typeof d === "object" ? (d as { msg?: unknown }).msg : undefined))
      .filter((m): m is string => typeof m === "string");
    if (msgs.length > 0) return new ApiError(msgs.join("; "), status);
  }
  return new ApiError(fallback, status);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError("Could not reach the server. Check your connection and try again.", 0);
  }

  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // Non-JSON error body; fall back to the generic message.
    }
    const error = errorFromBody(response.status, body);
    const retry = Number(response.headers.get("Retry-After"));
    if (Number.isFinite(retry) && retry > 0) error.retryAfter = Math.ceil(retry);
    throw error;
  }

  return (await response.json()) as T;
}

export const DEFAULT_CONFIG: AppConfig = {
  max_upload_mb: 5,
  accepted_extensions: [
    ".csv",
    ".tsv",
    ".txt",
    ".xlsx",
    ".ofx",
    ".qfx",
    ".pdf",
    ".xml",
    ".sta",
    ".mt940",
    ".940",
    ".dat",
  ],
  max_rows: 5000,
  max_pdf_pages: 20,
};

/** Loads server limits; never throws, falling back to defaults if the call fails. */
export async function fetchConfig(): Promise<AppConfig> {
  try {
    const raw = await request<Partial<AppConfig>>("/api/config");
    const extensions = Array.isArray(raw.accepted_extensions)
      ? raw.accepted_extensions
          .filter((e): e is string => typeof e === "string" && e.length > 0)
          .map((e) => (e.startsWith(".") ? e : `.${e}`).toLowerCase())
      : [];
    return {
      max_upload_mb:
        typeof raw.max_upload_mb === "number" && raw.max_upload_mb > 0
          ? raw.max_upload_mb
          : DEFAULT_CONFIG.max_upload_mb,
      accepted_extensions: extensions.length > 0 ? extensions : DEFAULT_CONFIG.accepted_extensions,
      max_rows: raw.max_rows ?? DEFAULT_CONFIG.max_rows,
      max_pdf_pages: raw.max_pdf_pages ?? DEFAULT_CONFIG.max_pdf_pages,
    };
  } catch {
    return DEFAULT_CONFIG;
  }
}

export function getCategories(): Promise<Category[]> {
  return request<Category[]>("/api/categories");
}

export function uploadStatement(
  file: File,
  convention: AmountConvention = "auto",
): Promise<StatementResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("amount_convention", convention);
  return request<StatementResult>("/api/statements", { method: "POST", body: form });
}

export function getStatement(id: string): Promise<StatementResult> {
  return request<StatementResult>(`/api/statements/${encodeURIComponent(id)}`);
}

export function correctTransaction(
  statementId: string,
  txnId: string,
  categoryId: string,
  applyToSimilar: boolean,
): Promise<CorrectionResponse> {
  return request<CorrectionResponse>(
    `/api/statements/${encodeURIComponent(statementId)}/transactions/${encodeURIComponent(txnId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category_id: categoryId, apply_to_similar: applyToSimilar }),
    },
  );
}

export function exportUrl(statementId: string): string {
  return `${API_BASE}/api/statements/${encodeURIComponent(statementId)}/export.csv`;
}
