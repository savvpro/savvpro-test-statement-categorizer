/**
 * API client for Statement Categorizer Backend.
 */

const API_BASE = '';

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error('API server is unreachable.');
  }
  return res.json();
}

export async function uploadStatement(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/api/statements/upload`, {
    method: 'POST',
    body: formData,
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to upload statement.');
  }
  return data;
}

export async function updateTransactionCategory(transactionId, category) {
  const res = await fetch(`${API_BASE}/api/transactions/${transactionId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ category }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Failed to update transaction category.');
  }
  return data;
}

export async function getCurrentStatement() {
  const res = await fetch(`${API_BASE}/api/statements/current`);
  if (!res.ok) {
    return null;
  }
  return res.json();
}

export async function getSampleCsv(formatType = 'standard') {
  const res = await fetch(`${API_BASE}/api/statements/sample?format_type=${formatType}`);
  if (!res.ok) {
    throw new Error('Failed to retrieve sample CSV.');
  }
  return res.text();
}
