import type {
  ImportOptions,
  ReviewInput,
  Statement,
  StatementListItem,
} from "./types";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, options);
  } catch {
    throw new Error(
      "Cannot reach the local server. Check that Ledgerly is running, then retry.",
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : "The request could not be completed. Check the fields and try again.",
    );
  }
  return response.json() as Promise<T>;
}

export const api = {
  list: () => request<StatementListItem[]>("/statements"),
  get: (id: string) => request<Statement>(`/statements/${id}`),
  upload: (file: File, options: ImportOptions) => {
    const body = new FormData();
    body.append("file", file);
    Object.entries(options).forEach(([key, value]) => body.append(key, value));
    return request<Statement>("/statements", { method: "POST", body });
  },
  review: (statementId: string, transactionId: string, body: ReviewInput) =>
    request<Statement>(
      `/statements/${statementId}/transactions/${transactionId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    ),
};

export function money(cents: number, currency = "USD") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(cents / 100);
}
export function shortDate(date: string) {
  return new Date(date + "T12:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}
