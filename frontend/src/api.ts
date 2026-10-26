export const baseurl = import.meta.env.VITE_API_URL || "http://localhost:8000"

export async function fetchapi(endpoint: string, options?: RequestInit) {
  const res = await fetch(`${baseurl}${endpoint}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || "API Error")
  }
  return res.json()
}