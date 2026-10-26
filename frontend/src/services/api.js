/**
 * API service for communicating with the Python FastAPI Backend.
 */

const API_BASE = '/api';

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function getCategories() {
  const res = await fetch(`${API_BASE}/categories`);
  if (!res.ok) throw new Error('Failed to load categories');
  return res.json();
}

export async function getSampleStatements() {
  const res = await fetch(`${API_BASE}/sample-statements`);
  if (!res.ok) throw new Error('Failed to load sample statements list');
  return res.json();
}

export async function loadSampleStatement(sampleId) {
  const res = await fetch(`${API_BASE}/sample-statements/${sampleId}`);
  if (!res.ok) throw new Error(`Failed to load sample statement ${sampleId}`);
  return res.json();
}

export async function uploadStatement(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to upload CSV' }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function addCustomRule(merchantPattern, category) {
  const res = await fetch(`${API_BASE}/custom-rule`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      merchant_pattern: merchantPattern,
      category: category,
    }),
  });
  if (!res.ok) throw new Error('Failed to save custom rule');
  return res.json();
}

export async function recalculateTransactions(transactions) {
  const res = await fetch(`${API_BASE}/recalculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(transactions),
  });
  if (!res.ok) throw new Error('Failed to recalculate tax summary');
  return res.json();
}
