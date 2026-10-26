/** Tiny API client. All requests are same-origin (Vite dev proxy or FastAPI static). */

export async function categorizeFile(file) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch('/api/categorize', { method: 'POST', body: fd })
  if (!res.ok) {
    let detail = `Upload failed (HTTP ${res.status})`
    try {
      const body = await res.json()
      if (body.detail) detail = body.detail
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }
  return res.json()
}
