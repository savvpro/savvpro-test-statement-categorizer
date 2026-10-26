const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

// Common API request handler
async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData
        ? {}
        : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
  });

  const raw = await response.text();

  let data = null;

  try {
    data = raw ? JSON.parse(raw) : null;
  } catch {
    data = raw;
  }

  if (!response.ok) {
    const detail =
      data?.detail ||
      data?.message ||
      data?.error ||
      (typeof data === 'string' ? data : null);

    throw new Error(detail || `Request failed (${response.status})`);
  }

  return data;
}

// Normalize transactions received from the backend
export function normalizeTransaction(row, index = 0) {
  const amount = Number(
    row.amount ?? row.transaction_amount ?? row.value ?? 0
  );

  const category =
    row.category ??
    row.predicted_category ??
    row.label ??
    'Needs Review';

  const confidence =
    row.confidence ?? row.category_confidence ?? null;

  const needsReview =
    row.needs_review ??
    row.needsReview ??
    row.review_required ??
    String(category).toLowerCase() === 'needs review';

  return {
    ...row,
    id: String(
      row.id ?? row.transaction_id ?? row.uuid ?? `row-${index}`
    ),
    date:
      row.date ??
      row.transaction_date ??
      row.posted_date ??
      '',
    description:
      row.description ??
      row.merchant ??
      row.payee ??
      row.memo ??
      row.narration ??
      'Unlabelled transaction',
    amount,
    category: String(category),
    confidence: confidence == null ? null : Number(confidence),
    needs_review: Boolean(needsReview),
  };
}

// Extract transaction rows from the API response
function rowsFrom(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }

  for (const key of ['transactions', 'results', 'data', 'items']) {
    if (Array.isArray(payload?.[key])) {
      return payload[key];
    }

    if (Array.isArray(payload?.[key]?.transactions)) {
      return payload[key].transactions;
    }
  }

  return [];
}

// Upload CSV/TSV statement to the FastAPI backend
export async function uploadStatement(file) {
  const body = new FormData();
  body.append('file', file);

  const payload = await request('/api/upload', {
    method: 'POST',
    body,
  });

  const transactions = rowsFrom(payload).map(normalizeTransaction);

  if (transactions.length === 0) {
    throw new Error(
      'File uploaded, but no transactions were returned by the backend.'
    );
  }

  return {
    payload,
    transactions,
    statementId:
      payload?.statement_id ??
      payload?.id ??
      payload?.statement?.id ??
      null,
  };
}

// Update a transaction's category
export async function updateTransactionCategory(transaction, category) {
  const body = JSON.stringify({ category });
  const id = encodeURIComponent(transaction.id);

  return request(`/api/transactions/${id}`, {
    method: 'PATCH',
    body,
  });
}

// Categories available in the frontend
export const CATEGORIES = [
  'Income',
  'Housing',
  'Groceries',
  'Dining',
  'Transport',
  'Shopping',
  'Utilities',
  'Healthcare',
  'Entertainment',
  'Subscriptions',
  'Transfer',
  'Refund',
  'Fees',
  'Education',
  'Travel',
  'Other',
  'Needs Review',
];