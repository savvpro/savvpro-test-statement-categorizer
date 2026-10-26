import type { Issue } from "./types";
export class ApiError extends Error {
  issues: Issue[];
  constructor(message: string, issues: Issue[] = []) {
    super(message);
    this.issues = issues;
  }
}
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError(
      "Cannot reach LedgerLens. Check that the backend is running, then retry.",
    );
  }
  if (!response.ok) {
    let body: { detail?: unknown; errors?: Issue[] } = {};
    try {
      body = await response.json();
    } catch {
      /* HTTP status remains actionable. */
    }
    throw new ApiError(
      typeof body.detail === "string"
        ? body.detail
        : `Request failed (${response.status}). Please check your inputs and retry.`,
      body.errors,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
export async function download(path: string, name: string) {
  const response = await fetch(`/api${path}`);
  if (!response.ok) {
    const body = await response.json();
    throw new ApiError(
      typeof body.detail === "string"
        ? body.detail
        : "Export failed. Please retry.",
    );
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function money(minor: number, currency: string) {
  // Presentation only. No financial aggregation or category totals happen in the browser.
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(minor / 100);
}
export function statusOf(row: {
  duplicate_status: string;
  needs_review: boolean;
  reviewed: boolean;
}) {
  return row.duplicate_status === "excluded"
    ? "Excluded"
    : row.needs_review
      ? "Needs review"
      : row.reviewed
        ? "Reviewed"
        : "Categorized";
}
