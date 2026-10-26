import { CategorizedTransaction, FinancialSummary, ParseResponse, TransactionType, BusinessCategory } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function parseStatementFile(file: File): Promise<ParseResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/statements/parse`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    let errorMsg = `Server error (${res.status})`;
    try {
      const errData = await res.json();
      if (errData.detail) {
        errorMsg = errData.detail;
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

export async function loadDemoStatement(): Promise<ParseResponse> {
  const res = await fetch(`${API_BASE}/api/demo`, {
    method: "GET",
  });

  if (!res.ok) {
    let errorMsg = `Server error (${res.status})`;
    try {
      const errData = await res.json();
      if (errData.detail) {
        errorMsg = errData.detail;
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

export async function recalculateSummary(
  transactions: CategorizedTransaction[]
): Promise<FinancialSummary> {
  const res = await fetch(`${API_BASE}/api/transactions/recalculate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ transactions }),
  });

  if (!res.ok) {
    throw new Error(`Failed to recalculate summary (${res.status})`);
  }

  return res.json();
}

export async function correctTransaction(
  transactionId: number,
  transactionType: TransactionType,
  businessCategory: BusinessCategory,
  transactions: CategorizedTransaction[]
): Promise<ParseResponse> {
  const res = await fetch(`${API_BASE}/api/transactions/correct`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      transaction_id: transactionId,
      update: {
        transaction_type: transactionType,
        business_category: businessCategory,
      },
      transactions,
    }),
  });

  if (!res.ok) {
    throw new Error(`Failed to correct transaction (${res.status})`);
  }

  return res.json();
}

export function exportTransactionsToCSV(
  transactions: CategorizedTransaction[],
  filename = "categorized_statement.csv"
) {
  const headers = [
    "Date",
    "Description",
    "Amount",
    "Transaction Type",
    "Business Category",
    "Review Status",
    "Confidence",
    "Rule ID",
    "Explanation",
    "Possible Duplicate",
    "Linked Purchase ID",
  ];

  const escapeCSV = (value: string | number | boolean | null | undefined) => {
    if (value === null || value === undefined) return '""';
    // Quoting alone does not stop spreadsheet formulas in merchant descriptions.
    const text = String(value);
    const safe = typeof value === "string" && /^[\s]*[=+@-]/.test(text)
      ? `'${text}` : text;
    const str = safe.replace(/"/g, '""');
    return `"${str}"`;
  };

  const rows = transactions.map((t) => [
    escapeCSV(t.date),
    escapeCSV(t.description),
    `"${t.amount}"`, // Validated Decimal; preserve the numeric sign for spreadsheets.
    escapeCSV(t.transaction_type),
    escapeCSV(t.business_category),
    escapeCSV(t.review_status),
    escapeCSV(t.confidence),
    escapeCSV(t.rule_id),
    escapeCSV(t.explanation),
    escapeCSV(t.is_possible_duplicate ? "Yes" : "No"),
    escapeCSV(t.linked_transaction_id ? `#${t.linked_transaction_id}` : ""),
  ]);

  const csvContent = [headers.map(escapeCSV).join(","), ...rows.map((r) => r.join(","))].join(
    "\r\n"
  );

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
