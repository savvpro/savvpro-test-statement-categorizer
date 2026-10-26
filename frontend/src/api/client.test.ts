import { describe, expect, it } from 'vitest'
import { ApiError, api } from './client'
import { errorResponse, mockFetch } from '../test/fixtures'

describe('api client', () => {
  it('throws ApiError carrying the backend detail, code and statement id', async () => {
    mockFetch({
      'POST /api/statements': () => errorResponse(409, 'already uploaded as statement 4', { code: 'duplicate_statement', statement_id: 4 }),
    })
    const error = await api
      .uploadStatement(new File(['x'], 'a.csv'), { accountType: 'checking', chargesPositive: true })
      .catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 409, message: 'already uploaded as statement 4', code: 'duplicate_statement', statementId: 4 })
  })

  it('sends charges_positive only when chosen', async () => {
    const fetch = mockFetch({ 'POST /api/statements': () => ({}) })
    await api.uploadStatement(new File(['x'], 'a.csv'), { accountType: 'credit_card', chargesPositive: false })
    expect((fetch.mock.calls[0][1]!.body as FormData).get('charges_positive')).toBe('false')
  })

  it('handles 204 and builds query strings', async () => {
    const fetch = mockFetch({
      'DELETE /api/statements/3': () => new Response(null, { status: 204 }),
      'GET /api/statements/3/transactions': () => [],
    })
    await expect(api.deleteStatement(3)).resolves.toBeUndefined()
    await api.listTransactions(3, 'needs_review')
    expect(fetch.mock.calls[1][0]).toBe('/api/statements/3/transactions?status=needs_review')
  })

  it('falls back to a generic message when the body is not JSON', async () => {
    mockFetch({ 'GET /api/health': () => new Response('<html>', { status: 502 }) })
    await expect(api.health()).rejects.toThrow('Request failed (502)')
  })
})
