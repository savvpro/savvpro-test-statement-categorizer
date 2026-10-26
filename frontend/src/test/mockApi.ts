import { vi } from 'vitest'

export interface Reply {
  status?: number
  json?: unknown
}

/** Return a reply for the request, or undefined for a request the test did not expect. */
export type Handler = (method: string, path: string, init?: RequestInit) => Reply | undefined

export function installFetch(handler: Handler) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    const method = (init?.method ?? 'GET').toUpperCase()
    const reply = handler(method, path, init)
    if (!reply) throw new Error(`Unexpected request: ${method} ${path}`)
    return new Response(JSON.stringify(reply.json ?? null), {
      status: reply.status ?? 200,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

/** The requests made so far, as "METHOD path" strings. */
export function requests(fetchMock: ReturnType<typeof installFetch>): string[] {
  return fetchMock.mock.calls.map(([input, init]) => {
    return `${(init?.method ?? 'GET').toUpperCase()} ${String(input)}`
  })
}
