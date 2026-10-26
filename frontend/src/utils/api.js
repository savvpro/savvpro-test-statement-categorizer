/**
 * Frontend API client communicating with FastAPI backend.
 */

const API_BASE = '/api';

/**
 * Upload a CSV bank or credit card statement.
 * @param {File} file
 * @returns {Promise<Object>} CategorizeResponse
 */
export async function uploadStatement(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    let errMsg = 'Failed to upload statement.';
    try {
      const errJson = await res.json();
      errMsg = errJson.detail || errMsg;
    } catch {
      errMsg = await res.text();
    }
    throw new Error(errMsg);
  }

  return res.json();
}

/**
 * Fetch pre-categorized sample statement for instant demo.
 * @returns {Promise<Object>} CategorizeResponse
 */
export async function loadSampleData() {
  const res = await fetch(`${API_BASE}/sample`);
  if (!res.ok) {
    let errMsg = 'Failed to load demo data.';
    try {
      const errJson = await res.json();
      errMsg = errJson.detail || errMsg;
    } catch {
      errMsg = await res.text();
    }
    throw new Error(errMsg);
  }
  return res.json();
}

/**
 * Recalculate IRS Schedule C summary from user-edited transactions.
 * @param {Array<Object>} transactions
 * @returns {Promise<Object>} TaxSummary
 */
export async function recalculateSummary(transactions) {
  const res = await fetch(`${API_BASE}/recalculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transactions }),
  });

  if (!res.ok) {
    let errMsg = 'Failed to recalculate tax summary.';
    try {
      const errJson = await res.json();
      errMsg = errJson.detail || errMsg;
    } catch {
      errMsg = await res.text();
    }
    throw new Error(errMsg);
  }

  return res.json();
}

/**
 * Get all IRS Schedule C tax categories and metadata.
 * @returns {Promise<Object>} Map of category names to metadata
 */
export async function getCategories() {
  const res = await fetch(`${API_BASE}/categories`);
  if (!res.ok) {
    throw new Error('Failed to fetch category definitions.');
  }
  return res.json();
}
