import {
  StatementPreviewResponse,
  SummaryResponse,
  Transaction,
  CategoryInfo,
} from '../types';

const API_BASE = '/api';

export async function fetchHealth(): Promise<{ status: string; app: string; version: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error('Backend service is unreachable.');
  }
  return res.json();
}

export async function fetchCategories(): Promise<CategoryInfo> {
  const res = await fetch(`${API_BASE}/categories`);
  if (!res.ok) {
    throw new Error('Failed to load categories.');
  }
  return res.json();
}

export async function uploadStatement(file: File): Promise<StatementPreviewResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/statements/preview`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Failed to process statement.' }));
    throw new Error(errorData.detail || `Upload failed with HTTP ${res.status}`);
  }

  return res.json();
}

export async function loadDemoStatement(): Promise<StatementPreviewResponse> {
  const res = await fetch(`${API_BASE}/statements/demo`, {
    method: 'POST',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Failed to load demo statement.' }));
    throw new Error(errorData.detail || 'Demo statement failed to load.');
  }

  return res.json();
}

export async function recalculateSummary(transactions: Transaction[]): Promise<SummaryResponse> {
  const res = await fetch(`${API_BASE}/summary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transactions }),
  });

  if (!res.ok) {
    throw new Error('Failed to recalculate summary.');
  }

  return res.json();
}

export async function exportTransactionsCsv(transactions: Transaction[]): Promise<Blob> {
  const res = await fetch(`${API_BASE}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transactions }),
  });

  if (!res.ok) {
    throw new Error('Failed to export CSV.');
  }

  return res.blob();
}
