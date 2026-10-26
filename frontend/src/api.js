const BASE = import.meta.env.VITE_API_URL ?? ''

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${BASE}${path}`, options)
  } catch {
    throw new Error('The API is not reachable. Start the backend (see README) and try again.')
  }
  if (response.status === 204) return null
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join('; ') : body.detail
    throw new Error(detail || `The request failed (${response.status}).`)
  }
  return body
}

const send = (method, data) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data),
})

const scoped = (path, statementId) => (statementId ? `${path}?statement_id=${statementId}` : path)

export const api = {
  meta: () => request('/api/meta'),
  statements: () => request('/api/statements'),
  upload(file, options) {
    const form = new FormData()
    form.append('file', file)
    Object.entries(options).forEach(([key, value]) => form.append(key, value))
    return request('/api/statements', { method: 'POST', body: form })
  },
  deleteStatement: (id) => request(`/api/statements/${id}`, { method: 'DELETE' }),
  deleteAll: () => request('/api/statements', { method: 'DELETE' }),
  transactions: (statementId) => request(scoped('/api/transactions', statementId)),
  correct: (id, category) => request(`/api/transactions/${id}`, send('PATCH', { category })),
  summary: (statementId) => request(scoped('/api/summary', statementId)),
  rules: () => request('/api/rules'),
  previewRule: (rule) => request('/api/rules/preview', send('POST', rule)),
  createRule: (rule) => request('/api/rules', send('POST', rule)),
  toggleRule: (id, enabled) => request(`/api/rules/${id}`, send('PATCH', { enabled })),
  deleteRule: (id) => request(`/api/rules/${id}`, { method: 'DELETE' }),
  exportUrl: (statementId) => `${BASE}${scoped('/api/export.csv', statementId)}`,
}
