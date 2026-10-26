import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import type { StatementDetail } from './api'

const categories = [
  'Software & Subscriptions',
  'Meals & Entertainment',
  'Client Income',
  'Transfer',
  'Needs Review',
]
const statement = {
  id: 1,
  filename: 'freelance.csv',
  created_at: '2026-09-30T10:00:00Z',
  transaction_count: 2,
  duplicate_count: 0,
}
const detail: StatementDetail = {
  statement,
  transactions: [
    {
      id: 1,
      statement_id: 1,
      row_number: 2,
      date: '2026-09-01',
      description: 'GITHUB COPILOT',
      amount: '-5600.00',
      transaction_type: '',
      category: 'Software & Subscriptions',
      automatic_category: 'Software & Subscriptions',
      manual_category: null,
      explanation: 'Outgoing payment matched GitHub subscription.',
      automatic_explanation: 'Outgoing payment matched GitHub subscription.',
      needs_review: false,
      manually_corrected: false,
      possible_duplicate: false,
      duplicate_confirmed: false,
    },
    {
      id: 2,
      statement_id: 1,
      row_number: 3,
      date: '2026-09-02',
      description: 'JOES CAFE 9921',
      amount: '-1250.00',
      transaction_type: '',
      category: 'Needs Review',
      automatic_category: 'Needs Review',
      manual_category: null,
      explanation:
        'The description does not establish a clear business category.',
      automatic_explanation:
        'The description does not establish a clear business category.',
      needs_review: true,
      manually_corrected: false,
      possible_duplicate: false,
      duplicate_confirmed: false,
    },
  ],
  summary: {
    currency: 'PKR',
    expenses: '5600.00',
    income: '0.00',
    refunds: '0.00',
    transfers: '0.00',
    transfers_in: '0.00',
    transfers_out: '0.00',
    unclassified_in: '0.00',
    unclassified_out: '1250.00',
    net_movement: '-6850.00',
    review_count: 1,
    transaction_count: 2,
    expense_categories: { 'Software & Subscriptions': '5600.00' },
  },
}

function respond(value: unknown, status = 200) {
  return Promise.resolve({
    ok: status < 400,
    status,
    json: async () => value,
  } as Response)
}

function mockServer(existing = true, initial = detail) {
  let saved = structuredClone(initial)
  const fetchMock = vi.fn((url: string, options?: RequestInit) => {
    if (url === '/api/categories') return respond(categories)
    if (url === '/api/statements') return respond(existing ? [statement] : [])
    if (url === '/api/statements/1') return respond(saved)
    if (url.endsWith('/confirm-duplicate')) {
      const id = Number(url.split('/').at(-2))
      saved.transactions = saved.transactions.map((row) =>
        row.id === id
          ? {
              ...row,
              duplicate_confirmed: true,
              needs_review: row.category === 'Needs Review',
            }
          : row,
      )
      saved.summary.review_count = saved.transactions.filter(
        (row) => row.needs_review,
      ).length
      return respond(saved)
    }
    if (options?.method === 'POST') return respond(saved, 201)
    if (options?.method === 'PATCH') {
      const category = JSON.parse(options.body as string).category
      const updatedTransactions = saved.transactions.map((row) =>
        row.id === 2
          ? {
              ...row,
              category,
              manual_category: category,
              manually_corrected: true,
              needs_review: row.possible_duplicate && !row.duplicate_confirmed,
              explanation: 'Category confirmed by you.',
            }
          : row,
      )
      saved = {
        ...saved,
        transactions: updatedTransactions,
        summary: {
          ...saved.summary,
          expenses: '6850.00',
          review_count: updatedTransactions.filter((row) => row.needs_review)
            .length,
          unclassified_out: '0.00',
        },
      }
      return respond(saved)
    }
    throw new Error(`Unexpected request: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

beforeEach(() => {
  mockServer()
})
afterEach(() => vi.unstubAllGlobals())

describe('statement workflow', () => {
  it('uploads a CSV and shows the imported transactions and summary', async () => {
    const fetchMock = mockServer(false)
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText('No statements imported yet.')
    await user.upload(
      screen.getByLabelText('Upload CSV statement'),
      new File(
        ['Date,Description,Amount\n2026-09-01,GITHUB COPILOT,-5600'],
        'freelance.csv',
        { type: 'text/csv' },
      ),
    )
    expect(await screen.findByText('GITHUB COPILOT')).toBeInTheDocument()
    expect(screen.getByText('1 transaction needs review')).toBeInTheDocument()
    expect(
      within(screen.getByLabelText('Statement summary')).getByText(
        'PKR 5,600.00',
      ),
    ).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/statements?filename=freelance.csv',
      expect.objectContaining({ method: 'POST', body: expect.any(File) }),
    )
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeEnabled()
  })

  it('searches and filters uncertain transactions', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText('GITHUB COPILOT')
    await user.click(screen.getByLabelText('Needs review only'))
    expect(screen.queryByText('GITHUB COPILOT')).not.toBeInTheDocument()
    expect(screen.getByText('JOES CAFE 9921')).toBeInTheDocument()
    await user.type(
      screen.getByLabelText('Search transactions'),
      'missing merchant',
    )
    expect(screen.getByText(/No matching transactions/)).toBeInTheDocument()
    await user.clear(screen.getByLabelText('Search transactions'))
    await user.click(screen.getByLabelText('Needs review only'))
    await user.selectOptions(
      screen.getByLabelText('Filter by category'),
      'Software & Subscriptions',
    )
    expect(screen.getByText('GITHUB COPILOT')).toBeInTheDocument()
    expect(screen.queryByText('JOES CAFE 9921')).not.toBeInTheDocument()
  })

  it('saves a category correction, refreshes totals and restores it on reload', async () => {
    const user = userEvent.setup()
    const view = render(<App />)
    await screen.findByText('JOES CAFE 9921')
    await user.selectOptions(
      screen.getByLabelText('Category for JOES CAFE 9921, row 3'),
      'Meals & Entertainment',
    )
    expect(await screen.findByText('Corrected')).toBeInTheDocument()
    expect(screen.getByText('No transactions need review')).toBeInTheDocument()
    expect(
      within(screen.getByLabelText('Statement summary')).getByText(
        'PKR 6,850.00',
      ),
    ).toBeInTheDocument()
    view.unmount()
    render(<App />)
    expect(await screen.findByText('Corrected')).toBeInTheDocument()
    expect(
      screen.getByLabelText('Category for JOES CAFE 9921, row 3'),
    ).toHaveValue('Meals & Entertainment')
  })

  it('shows import errors and keeps the previous statement', async () => {
    const fetchMock = mockServer()
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText('GITHUB COPILOT')
    fetchMock.mockImplementationOnce(() =>
      respond(
        { detail: 'Row 3: date must be YYYY-MM-DD. Nothing was imported.' },
        422,
      ),
    )
    await user.upload(
      screen.getByLabelText('Upload CSV statement'),
      new File(['invalid'], 'broken.csv', { type: 'text/csv' }),
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Row 3: date must be YYYY-MM-DD',
    )
    expect(screen.getByText('GITHUB COPILOT')).toBeInTheDocument()
  })

  it('preserves the category and totals when a correction fails', async () => {
    const fetchMock = mockServer()
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText('JOES CAFE 9921')
    fetchMock.mockImplementationOnce(() =>
      respond(
        { detail: 'The local database is unavailable. Please try again.' },
        503,
      ),
    )
    const category = screen.getByLabelText('Category for JOES CAFE 9921, row 3')
    await user.selectOptions(category, 'Meals & Entertainment')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The local database is unavailable.',
    )
    expect(category).toHaveValue('Needs Review')
    expect(category).toBeEnabled()
    expect(screen.queryByText('Corrected')).not.toBeInTheDocument()
    expect(
      within(screen.getByLabelText('Statement summary')).getByText(
        'PKR 5,600.00',
      ),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeEnabled()
  })

  it('downloads the categorized CSV', async () => {
    const fetchMock = mockServer()
    const user = userEvent.setup()
    const createUrl = vi.fn(() => 'blob:categorized-statement')
    vi.stubGlobal('URL', {
      createObjectURL: createUrl,
      revokeObjectURL: vi.fn(),
    })
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {})
    render(<App />)
    await screen.findByText('GITHUB COPILOT')
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        blob: async () => new Blob(['Date,Description,Amount']),
      } as Response),
    )
    await user.click(screen.getByRole('button', { name: 'Export CSV' }))
    await waitFor(() => expect(click).toHaveBeenCalledOnce())
    expect(createUrl).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenLastCalledWith('/api/statements/1/export')
  })

  it('confirms a duplicate without marking its category corrected', async () => {
    const repeated = structuredClone(detail)
    repeated.transactions[0].possible_duplicate = true
    repeated.transactions[0].needs_review = true
    repeated.summary.review_count = 2
    const fetchMock = mockServer(true, repeated)
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText('GITHUB COPILOT')
    await user.click(screen.getByRole('button', { name: 'Confirm entry' }))
    expect(
      await screen.findByText('Repeated entry confirmed · retained'),
    ).toBeInTheDocument()
    expect(
      screen.getByLabelText('Category for GITHUB COPILOT, row 2'),
    ).toHaveValue('Software & Subscriptions')
    expect(screen.queryByText('Corrected')).not.toBeInTheDocument()
    expect(screen.getByText('1 transaction needs review')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/statements/1/transactions/1/confirm-duplicate',
      { method: 'POST' },
    )
  })

  it('keeps a corrected duplicate under review until confirmed separately', async () => {
    const repeated = structuredClone(detail)
    repeated.transactions[1].possible_duplicate = true
    const fetchMock = mockServer(true, repeated)
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText('JOES CAFE 9921')
    await user.selectOptions(
      screen.getByLabelText('Category for JOES CAFE 9921, row 3'),
      'Meals & Entertainment',
    )
    expect(await screen.findByText('Category corrected')).toBeInTheDocument()
    expect(screen.getByText('1 transaction needs review')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirm entry' })).toBeEnabled()
    expect(
      fetchMock.mock.calls.filter(([, options]) => options?.method === 'PATCH'),
    ).toHaveLength(1)
    await user.click(screen.getByRole('button', { name: 'Confirm entry' }))
    expect(
      await screen.findByText('No transactions need review'),
    ).toBeInTheDocument()
    expect(screen.getByText('Corrected')).toBeInTheDocument()
    expect(
      screen.getByLabelText('Category for JOES CAFE 9921, row 3'),
    ).toHaveValue('Meals & Entertainment')
  })
})
