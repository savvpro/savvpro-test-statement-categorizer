import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import App from './App'
import { baseRoutes, cafe, deposit, detail, errorResponse, mockFetch, summary, txn } from './test/fixtures'
import type { Transaction } from './api/types'

const rows = [txn(), cafe, deposit]

function uploadRoutes(transactions: Transaction[] = rows) {
  return {
    ...baseRoutes(),
    'POST /api/statements': () => new Response(JSON.stringify({ ...detail, transactions }), { status: 201 }),
    'GET /api/statements/7/summary': () => summary,
    'GET /api/statements/7/transactions': () => transactions,
  }
}

async function uploadFile() {
  const user = userEvent.setup()
  const file = new File(['Date,Description,Amount\n'], 'credit_card.csv', { type: 'text/csv' })
  await user.selectOptions(screen.getByLabelText('Account type'), 'credit_card')
  await user.upload(screen.getByTestId('file-input'), file)
  return user
}

describe('App', () => {
  it('uploads a file with POST and renders the rows and summary', async () => {
    const fetch = mockFetch(uploadRoutes())
    render(<App />)
    await uploadFile()

    expect(await screen.findByText('SQ *JOES CAFE 9921')).toBeInTheDocument()
    const post = fetch.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(post).toBeDefined()
    const form = post![1]!.body as FormData
    expect(form.get('account_type')).toBe('credit_card')
    expect((form.get('file') as File).name).toBe('credit_card.csv')
    expect(form.has('charges_positive')).toBe(false)

    expect(screen.getByTestId('stat-Income')).toHaveTextContent('$2,500.00')
    expect(screen.getByTestId('stat-Needs review')).toHaveTextContent('1')
    expect(screen.getByText(/invalid date/)).toBeInTheDocument()
  })

  it('opens on Needs Review when rows need review, and tabs filter', async () => {
    mockFetch(uploadRoutes())
    render(<App />)
    const user = await uploadFile()

    const reviewTab = await screen.findByRole('tab', { name: /Needs Review/ })
    expect(reviewTab).toHaveAttribute('aria-selected', 'true')
    expect(reviewTab).toHaveTextContent('1')
    const table = screen.getByRole('table', { name: 'Transactions' })
    expect(within(table).getByText('SQ *JOES CAFE 9921')).toBeInTheDocument()
    expect(within(table).queryByLabelText('Category for ADOBE CREATIVE CLOUD')).not.toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: /All/ }))
    expect(screen.getByLabelText('Category for ADOBE CREATIVE CLOUD')).toBeInTheDocument()
    expect(screen.getByText('ACH DEPOSIT HARBOR & PINE CO')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: /Auto/ }))
    expect(screen.queryByText('SQ *JOES CAFE 9921')).not.toBeInTheDocument()
  })

  it('saves a category with remember=true, refetches and shows the toast', async () => {
    const confirmed = { ...cafe, category_id: 'meals', status: 'user_confirmed' as const, updated_at: '2026-01-11T00:00:00Z' }
    let saved = false
    const fetch = mockFetch({
      ...uploadRoutes(),
      'GET /api/statements/7/transactions': () => (saved ? [txn(), confirmed, deposit] : rows),
      'PATCH /api/transactions/2': () => {
        saved = true
        return { transaction: confirmed, updated_count: 3 }
      },
    })
    render(<App />)
    const user = await uploadFile()

    const select = await screen.findByLabelText('Category for SQ *JOES CAFE 9921')
    expect(select).toHaveValue('meals') // pre-filled with the suggestion
    const row = select.closest('tr')!
    await user.click(within(row).getByLabelText('Remember for this merchant'))
    await user.click(within(row).getByRole('button', { name: 'Save' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Updated 3 other transactions')
    const patch = fetch.mock.calls.find(([, init]) => init?.method === 'PATCH')!
    expect(JSON.parse(patch[1]!.body as string)).toEqual({ category_id: 'meals', remember: true })
    const calls = fetch.mock.calls.map(([url, init]) => `${init?.method ?? 'GET'} ${url}`)
    expect(calls.filter((c) => c === 'GET /api/statements/7/summary')).toHaveLength(2)
    expect(calls).toContain('GET /api/statements/7/transactions')
    await waitFor(() => expect(screen.getByRole('tab', { name: /Needs Review/ })).toHaveTextContent('0'))
  })

  it("shows the backend's error message in a banner", async () => {
    mockFetch({
      ...baseRoutes(),
      'POST /api/statements': () =>
        errorResponse(400, 'could not read junk.csv: no header row found in the first 30 rows'),
    })
    render(<App />)
    await uploadFile()
    expect(await screen.findByRole('alert')).toHaveTextContent('no header row found')
  })

  it('offers to open the existing statement on a duplicate upload', async () => {
    mockFetch({
      ...uploadRoutes(),
      'POST /api/statements': () =>
        errorResponse(409, 'already uploaded', { code: 'duplicate_statement', statement_id: 7 }),
      'GET /api/statements/7': () => detail,
    })
    render(<App />)
    const user = await uploadFile()
    await user.click(await screen.findByRole('button', { name: 'Open existing statement' }))
    expect(await screen.findByText('SQ *JOES CAFE 9921')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows a clear message when the server is unreachable', async () => {
    const fetch = mockFetch({})
    fetch.mockRejectedValue(new TypeError('Failed to fetch'))
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the server')
  })
})
