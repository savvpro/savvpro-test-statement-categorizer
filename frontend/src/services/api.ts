import type { CategorizationResponse, CategorizedTransaction } from "../types";

const API_BASE = "http://localhost:8000/api";

export async function getCategories(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/categories`);
  if (!res.ok) {
    throw new Error("Failed to fetch tax categories.");
  }
  return res.json();
}

export async function uploadStatement(file: File): Promise<CategorizationResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed with HTTP ${res.status}`);
  }

  return res.json();
}

export async function recalculateStatement(
  transactions: CategorizedTransaction[],
  filename: string
): Promise<CategorizationResponse> {
  const res = await fetch(`${API_BASE}/recalculate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transactions, filename }),
  });

  if (!res.ok) {
    throw new Error("Failed to recalculate metrics.");
  }

  return res.json();
}

export async function submitRuleCorrection(
  transactionId: string,
  newCategory: string,
  saveAsRule: boolean,
  rulePattern?: string
): Promise<void> {
  await fetch(`${API_BASE}/correct`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      transaction_id: transactionId,
      new_category: newCategory,
      save_as_rule: saveAsRule,
      rule_pattern: rulePattern,
    }),
  });
}

export async function exportCategorizedCsv(data: CategorizationResponse): Promise<void> {
  const res = await fetch(`${API_BASE}/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error("Failed to generate CSV export.");
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const baseName = data.filename ? data.filename.replace(/\.[^/.]+$/, "") : "statement";
  a.download = `${baseName}_categorized_tax_report.csv`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}
