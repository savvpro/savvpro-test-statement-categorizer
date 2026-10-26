import type { CategorizeResponse } from './types'

const API_BASE = ''

export async function uploadStatement(file: File): Promise<CategorizeResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/api/categorize`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Upload failed')
  }
  return res.json()
}

export async function fetchCategories(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/categories`)
  if (!res.ok) throw new Error('Failed to load categories')
  const data = await res.json()
  return data.categories as string[]
}

export async function updateTransactionCategory(
  transactionId: string,
  category: string,
): Promise<CategorizeResponse> {
  const res = await fetch(`${API_BASE}/api/transactions`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transaction_id: transactionId, category }),
  })
  if (!res.ok) throw new Error('Failed to update category')
  return res.json()
}
