import { describe, expect, it } from 'vitest'
import { installFetch } from '../test/mockApi'
import { ApiError, correctTransaction, exportUrl, getStatement, uploadStatement } from './client'

describe('API client errors', () => {
  it('surfaces the API detail message', async () => {
    installFetch(() => ({ status: 404, json: { detail: 'Statement 9 not found' } }))
    await expect(getStatement(9)).rejects.toMatchObject({
      message: 'Statement 9 not found',
      status: 404,
    })
  })

  it('turns a validation error list into one readable message', async () => {
    installFetch(() => ({
      status: 422,
      json: {
        detail: [{ loc: ['body', 'category'], msg: "Input should be 'Meals' or 'Travel'" }],
      },
    }))
    await expect(correctTransaction(1, { category: 'x', remember: false })).rejects.toThrow(
      "category: Input should be 'Meals' or 'Travel'",
    )
  })

  it('falls back to the status when the body is not JSON', async () => {
    const response = new Response('<html>Bad gateway</html>', { status: 502 })
    globalThis.fetch = async () => response
    await expect(getStatement(1)).rejects.toThrow('Request failed (HTTP 502)')
  })

  it('reports an unreachable server', async () => {
    globalThis.fetch = async () => {
      throw new TypeError('Failed to fetch')
    }
    const error = await getStatement(1).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).message).toMatch(/cannot reach the server/i)
  })
})

describe('API client requests', () => {
  it('uploads the file as multipart form data', async () => {
    const fetchMock = installFetch(() => ({ status: 201, json: { id: 1 } }))
    await uploadStatement(new File(['x'], 'a.csv'))
    const [path, init] = fetchMock.mock.calls[0]
    expect(path).toBe('/api/statements')
    expect(init?.method).toBe('POST')
    const form = init?.body as FormData
    expect(form.get('file')).toBeInstanceOf(File)
  })

  it('sends a correction as JSON and leaves out an unset kind', async () => {
    const fetchMock = installFetch(() => ({ json: { reclassified_count: 0 } }))
    await correctTransaction(7, { category: 'Meals', remember: true })
    const [path, init] = fetchMock.mock.calls[0]
    expect(path).toBe('/api/transactions/7')
    expect(init?.method).toBe('PATCH')
    expect(JSON.parse(String(init?.body))).toEqual({ category: 'Meals', remember: true })
  })

  it('builds the export URL', () => {
    expect(exportUrl(3)).toBe('/api/statements/3/export')
  })
})
