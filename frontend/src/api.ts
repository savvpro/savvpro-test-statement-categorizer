import type {
  AuditEvent,
  ReviewInput,
  RowError,
  Statement,
  StatementListItem,
  Transaction,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public rows: RowError[] = [],
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError(
      "Could not reach the server. Check that the Python backend is running.",
      0,
    );
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const message =
      typeof payload.detail === "string"
        ? payload.detail
        : "Request could not be completed. Check the form and try again.";
    throw new ApiError(message, response.status, payload.errors ?? []);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const api = {
  list: () => request<StatementListItem[]>("/statements"),
  statement: (id: string) => request<Statement>(`/statements/${id}`),
  import: (body: FormData) =>
    request<{ id: string; reused: boolean }>("/statements", {
      method: "POST",
      body,
    }),
  review: (id: string, body: ReviewInput) =>
    request<Transaction>(`/transactions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  audit: (id: string) => request<AuditEvent[]>(`/statements/${id}/audit`),
  delete: (id: string) =>
    request<void>(`/statements/${id}`, { method: "DELETE" }),
  async sample(): Promise<File> {
    const response = await fetch("/api/sample");
    if (!response.ok)
      throw new ApiError(
        "Could not load the sample statement.",
        response.status,
      );
    return new File([await response.blob()], "designer-bank.csv", {
      type: "text/csv",
    });
  },
  async download(id: string, final: boolean, summary = false) {
    const response = await fetch(
      `/api/statements/${id}/export?final=${final}&summary=${summary}`,
    );
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new ApiError(
        payload.detail ?? "Export failed. Try again.",
        response.status,
      );
    }
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `${final ? "final" : "draft"}-${summary ? "summary" : "transactions"}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};

export const money = (minor: number, currency = "USD") =>
  new Intl.NumberFormat("en-US", { style: "currency", currency }).format(
    minor / 100,
  );
// Parse the date at noon UTC, so a user's timezone cannot move a statement row to another date.
export const displayDate = (iso: string) =>
  new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${iso}T12:00:00Z`));
export const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : "Something went wrong. Try again.";
