import { ApiError } from "./api/client";

export interface FriendlyError {
  title: string;
  message: string;
}

const TITLES: Record<string, string> = {
  file_too_large: "File is too large",
  empty_file: "The file is empty",
  unsupported_format: "Unsupported file type",
  file_corrupt: "The file could not be read",
  pdf_encrypted: "The PDF is password protected",
  pdf_no_text: "No text found in the PDF",
  pdf_too_many_pages: "The PDF has too many pages",
  too_many_rows: "Too many rows",
  no_transactions_found: "No transactions found",
  missing_columns: "Required columns are missing",
  rate_limited: "Too many requests",
  statement_not_found: "Statement not found",
  invalid_category: "Invalid category",
  invalid_request: "Invalid request",
  transaction_not_found: "Transaction not found",
  not_found: "Not found",
  method_not_allowed: "Action not allowed",
  internal_error: "Something went wrong on our side",
};

// Extra guidance appended to the server message for cases the user can act on.
const HINTS: Record<string, string> = {
  pdf_no_text:
    "This looks like a scanned image. Try exporting a CSV from your bank's website instead.",
  pdf_encrypted: "Remove the password in your PDF viewer, or export a CSV from your bank.",
};

const SERVER_FAULT_MESSAGE = "Something went wrong on our side. Please try again in a moment.";

export function describeError(err: unknown): FriendlyError {
  if (err instanceof ApiError) {
    const code = err.code ?? "";
    if (code === "internal_error" || err.status >= 500) {
      return { title: TITLES.internal_error, message: SERVER_FAULT_MESSAGE };
    }
    const title = TITLES[code] ?? "Something went wrong";
    const hint = HINTS[code];
    return { title, message: hint ? `${err.message} ${hint}` : err.message };
  }
  return {
    title: "Something went wrong",
    message: err instanceof Error ? err.message : "Please try again.",
  };
}

export function isRateLimited(err: unknown): err is ApiError {
  return err instanceof ApiError && (err.code === "rate_limited" || err.status === 429);
}
