const BASE = import.meta.env.VITE_API_URL || ''

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, options)
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`)
  return body
}

export const getCategories = () => request('/api/categories')

export const uploadStatement = (file) => {
  const form = new FormData()
  form.append('file', file)
  return request('/api/statements', { method: 'POST', body: form })
}

export const reviewTransaction = (sid, txId, category, applyToSameMerchant = true) =>
  request(`/api/statements/${sid}/transactions/${txId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category, apply_to_same_merchant: applyToSameMerchant }),
  })
