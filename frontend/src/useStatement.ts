import { useCallback, useEffect, useRef, useState } from 'react'
import {
  errorMessage,
  getStatement,
  getSummary,
  type StatementDetail,
  type StatementSummary,
} from './api/client'

export type LoadStatus = 'idle' | 'loading' | 'ready' | 'error'

type Result =
  | { id: number; detail: StatementDetail; summary: StatementSummary; error?: undefined }
  | { id: number; error: string; detail?: undefined; summary?: undefined }

async function fetchStatement(id: number): Promise<Result> {
  try {
    const [detail, summary] = await Promise.all([getStatement(id), getSummary(id)])
    return { id, detail, summary }
  } catch (caught) {
    return { id, error: errorMessage(caught) }
  }
}

/**
 * Loads one statement and its summary. The status is worked out from what has arrived, so
 * a statement that is still loading never shows the previous one. `reload` refreshes the
 * open statement in place, without going back to the loading state.
 */
export function useStatement(id: number | null) {
  const [result, setResult] = useState<Result | null>(null)
  const latest = useRef(0)

  const apply = useCallback((request: number, next: Result) => {
    if (request !== latest.current) return // a newer request replaced this one
    // a failed refresh keeps what is already on screen
    setResult((previous) =>
      next.error && previous?.id === next.id && previous.detail ? previous : next,
    )
  }, [])

  useEffect(() => {
    const request = ++latest.current
    if (id === null) return
    void fetchStatement(id).then((next) => apply(request, next))
  }, [id, apply])

  const reload = useCallback(async () => {
    if (id === null) return
    const request = ++latest.current
    apply(request, await fetchStatement(id))
  }, [id, apply])

  const current = id !== null && result?.id === id ? result : null
  const status: LoadStatus =
    id === null ? 'idle' : !current ? 'loading' : current.error !== undefined ? 'error' : 'ready'

  return {
    detail: current?.detail ?? null,
    summary: current?.summary ?? null,
    status,
    error: current?.error ?? '',
    reload,
  }
}
