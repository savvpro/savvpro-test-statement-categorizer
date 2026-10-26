import type { CategorizeResponse } from "./types";

const configuredApiUrl = import.meta.env.VITE_API_URL?.trim() || "/api";
const apiBaseUrl = configuredApiUrl.replace(/\/+$/, "");

export async function categorizeStatement(
  file: File,
): Promise<CategorizeResponse> {
  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/categorize`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new Error(
      "Could not reach the categorization service. Check that the backend is running and the API URL is correct.",
    );
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : `The server returned an error (${response.status}).`;
    throw new Error(detail);
  }

  if (
    typeof payload !== "object" ||
    payload === null ||
    !("transactions" in payload) ||
    !Array.isArray(payload.transactions) ||
    !("invalid_rows" in payload) ||
    !Array.isArray(payload.invalid_rows) ||
    !("category_totals" in payload) ||
    typeof payload.category_totals !== "object" ||
    payload.category_totals === null ||
    !("total_rows" in payload) ||
    typeof payload.total_rows !== "number"
  ) {
    throw new Error("The server returned an unexpected response.");
  }

  return payload as CategorizeResponse;
}
