import type {
  UploadResponse,
  SummaryResponse,
  TransactionUpdate,
  UpdateTransactionResponse,
} from "../types";

const API_BASE = "";

export async function uploadCsv(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed: ${response.status}`);
  }

  return response.json();
}

export async function updateTransaction(
  id: string,
  update: TransactionUpdate
): Promise<UpdateTransactionResponse> {
  const response = await fetch(`${API_BASE}/api/transactions/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Update failed: ${response.status}`
    );
  }

  return response.json();
}

export async function getSummary(): Promise<SummaryResponse> {
  const response = await fetch(`${API_BASE}/api/summary`);

  if (!response.ok) {
    throw new Error(`Summary failed: ${response.status}`);
  }

  return response.json();
}

export async function exportCsv(): Promise<Blob> {
  const response = await fetch(`${API_BASE}/api/export`);

  if (!response.ok) {
    throw new Error(`Export failed: ${response.status}`);
  }

  return response.blob();
}

export function downloadCsv(blob: Blob, filename: string = "categorized.csv") {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
