import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { StatementDetail, Transaction } from './api/client'
import App from './App'
import { installFetch, requests } from './test/mockApi'
import {
  CATEGORIES,
  listItem,
  makeDetail,
  makeReviewRow,
  makeSummary,
  makeTransaction,
  TWO_CURRENCIES,
} from './test/fixtures'

function csvFile(name = 'bank_a_card.csv') {
  return new File(['Date,Description,Amount,Currency\n'], name, { type: 'text/csv' })
}

describe('uploading', () => {
  it('shows the uploaded statement', async () => {
    const detail = makeDetail([makeTransaction(), makeReviewRow()])
    let uploaded = false
    const fetchMock = installFetch((method, path) => {
      if (path === '/api/categories') return { json: CATEGORIES }
      if (path === '/api/statements' && method === 'GET') {
        return { json: uploaded ? [listItem(detail)] : [] }
      }
      if (path === '/api/statements' && method === 'POST') {
        uploaded = true
        return { status: 201, json: detail }
      }
      if (path === '/api/statements/1') return { json: detail }
      if (path === '/api/statements/1/summary') return { json: TWO_CURRENCIES }
    })
    const user = userEvent.setup()
    render(<App />)

    expect(await screen.findByText(/no statements yet/i)).toBeInTheDocument()
    await user.upload(screen.getByLabelText(/statement file/i), csvFile())
    await user.click(screen.getByRole('button', { name: /upload and categorize/i }))

    expect(await screen.findByRole('heading', { name: 'bank_a_card.csv' })).toBeInTheDocument()
    expect(screen.getByText('ADOBE CREATIVE CLOUD SAN JOSE CA')).toBeInTheDocument()
    expect(screen.getByText('XYZ TRADERS 4471 RAWALPINDI')).toBeInTheDocument()
    // the counts bar
    const counts = screen.getByLabelText('Statement counts')
    expect(within(counts).getByText('Auto-categorized').nextSibling).toHaveTextContent('1')
    expect(within(counts).getByText('Needs review').nextSibling).toHaveTextContent('1')
    // the file went up as a multipart form
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    const body = post?.[1]?.body as FormData
    expect((body.get('file') as File).name).toBe('bank_a_card.csv')
  })

  it('shows the API message when the upload is rejected', async () => {
    const message =
      "Unrecognised header row: 'a,b'. Supported formats: bank_a_card: Date,Description,Amount,Currency"
    const fetchMock = installFetch((method, path) => {
      if (path === '/api/categories') return { json: CATEGORIES }
      if (path === '/api/statements' && method === 'GET') return { json: [] }
      if (path === '/api/statements' && method === 'POST') {
        return { status: 400, json: { detail: message } }
      }
    })
    const user = userEvent.setup()
    render(<App />)

    await screen.findByText(/no statements yet/i)
    await user.upload(screen.getByLabelText(/statement file/i), csvFile('other.csv'))
    await user.click(screen.getByRole('button', { name: /upload and categorize/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(message)
    expect(requests(fetchMock)).not.toContain('GET /api/statements/1')
    expect(screen.queryByRole('heading', { name: 'other.csv' })).not.toBeInTheDocument()
  })

  it('shows the size message for a 413', async () => {
    installFetch((method, path) => {
      if (path === '/api/categories') return { json: CATEGORIES }
      if (path === '/api/statements' && method === 'GET') return { json: [] }
      if (path === '/api/statements' && method === 'POST') {
        return { status: 413, json: { detail: 'File is larger than 5 MB' } }
      }
    })
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText(/no statements yet/i)
    await user.upload(screen.getByLabelText(/statement file/i), csvFile())
    await user.click(screen.getByRole('button', { name: /upload and categorize/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('File is larger than 5 MB')
  })

  it('asks for a file before uploading', async () => {
    installFetch((method, path) => {
      if (path === '/api/categories') return { json: CATEGORIES }
      if (path === '/api/statements' && method === 'GET') return { json: [] }
    })
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText(/no statements yet/i)
    await user.click(screen.getByRole('button', { name: /upload and categorize/i }))
    expect(screen.getByRole('alert')).toHaveTextContent(/choose a .csv file/i)
  })
})

describe('fixing a row', () => {
  function setup(reclassified = 0, patchStatus = 200) {
    let row: Transaction = makeReviewRow()
    const fetchMock = installFetch((method, path, init) => {
      const detail = () => makeDetail([makeTransaction(), row])
      if (path === '/api/categories') return { json: CATEGORIES }
      if (path === '/api/statements') return { json: [listItem(detail())] }
      if (path === '/api/statements/1') return { json: detail() }
      if (path === '/api/statements/1/summary') return { json: makeSummary() }
      if (path === '/api/transactions/18' && method === 'PATCH') {
        if (patchStatus !== 200) {
          return { status: patchStatus, json: { detail: 'Cannot remember this merchant' } }
        }
        const body = JSON.parse(String(init?.body)) as { category: string }
        row = {
          ...row,
          category: body.category,
          needs_review: false,
          edited_by_user: true,
          confidence: 1,
          rule_id: 'manual',
          reason: 'set by you',
        }
        return { json: { transaction: row, reclassified_count: reclassified } }
      }
    })
    return fetchMock
  }

  async function openStatement(user: ReturnType<typeof userEvent.setup>) {
    render(<App />)
    await user.click(await screen.findByRole('button', { name: /bank_a_card\.csv/ }))
    await screen.findByText('XYZ TRADERS 4471 RAWALPINDI')
  }

  it('sends the right PATCH and refreshes the table', async () => {
    const fetchMock = setup(2)
    const user = userEvent.setup()
    await openStatement(user)

    const row = screen.getByRole('row', { name: /XYZ TRADERS/ })
    expect(within(row).getByText('Needs review')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Fix row 18' }))
    await user.selectOptions(screen.getByLabelText('Category'), 'Travel')
    await user.click(screen.getByLabelText(/remember for this merchant/i))
    await user.click(screen.getByRole('button', { name: 'Save' }))

    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')
    expect(String(patch?.[0])).toBe('/api/transactions/18')
    expect(JSON.parse(String(patch?.[1]?.body))).toEqual({ category: 'Travel', remember: true })

    expect(await screen.findByText('Saved. 2 other rows updated.')).toBeInTheDocument()
    await waitFor(() => {
      const fixed = screen.getByRole('row', { name: /XYZ TRADERS/ })
      expect(within(fixed).getByText('Travel')).toBeInTheDocument()
      expect(within(fixed).getByText('Fixed by me')).toBeInTheDocument()
      expect(within(fixed).getByText('set by you')).toBeInTheDocument()
      expect(within(fixed).queryByText('Needs review')).not.toBeInTheDocument()
    })
    expect(screen.queryByRole('form')).not.toBeInTheDocument() // the editor closed
    // the statement, its summary and the list were all fetched again
    const calls = requests(fetchMock)
    expect(calls.filter((c) => c === 'GET /api/statements/1')).toHaveLength(2)
    expect(calls.filter((c) => c === 'GET /api/statements/1/summary')).toHaveLength(2)
  })

  it('sends the chosen kind, and says plainly when no other rows changed', async () => {
    const fetchMock = setup(0)
    const user = userEvent.setup()
    await openStatement(user)

    await user.click(screen.getByRole('button', { name: 'Fix row 18' }))
    await user.selectOptions(screen.getByLabelText('Category'), 'Personal')
    await user.selectOptions(screen.getByLabelText(/kind/i), 'fee')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')
    expect(JSON.parse(String(patch?.[1]?.body))).toEqual({
      category: 'Personal',
      kind: 'fee',
      remember: false,
    })
    expect(await screen.findByText('Saved.')).toBeInTheDocument()
  })

  it('does not offer Needs Review as a category and cannot save without one', async () => {
    setup()
    const user = userEvent.setup()
    await openStatement(user)
    await user.click(screen.getByRole('button', { name: 'Fix row 18' }))

    const options = within(screen.getByLabelText('Category')).getAllByRole('option')
    expect(options.map((o) => o.textContent)).not.toContain('Needs Review')
    expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled()
  })

  it('shows the API error inside the editor and keeps it open', async () => {
    setup(0, 422)
    const user = userEvent.setup()
    await openStatement(user)
    await user.click(screen.getByRole('button', { name: 'Fix row 18' }))
    await user.selectOptions(screen.getByLabelText('Category'), 'Travel')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot remember this merchant')
    expect(screen.getByLabelText('Category')).toBeInTheDocument()
  })

  it('lets any row be edited, and cancel closes the editor', async () => {
    setup()
    const user = userEvent.setup()
    await openStatement(user)

    await user.click(screen.getByRole('button', { name: 'Edit row 1' }))
    expect(screen.getByLabelText('Category')).toHaveValue('Software & Subscriptions')
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByLabelText('Category')).not.toBeInTheDocument()
  })
})

describe('the open statement', () => {
  function setupTwo(): { first: StatementDetail; second: StatementDetail } {
    const first = makeDetail([makeTransaction({ raw_description: 'FIRST FILE ROW' })], { id: 1 })
    const second = makeDetail([makeTransaction({ id: 2, raw_description: 'SECOND FILE ROW' })], {
      id: 2,
      filename: 'bank_b_checking.csv',
    })
    installFetch((_method, path) => {
      if (path === '/api/categories') return { json: CATEGORIES }
      if (path === '/api/statements') return { json: [listItem(second), listItem(first)] }
      if (path === '/api/statements/1') return { json: first }
      if (path === '/api/statements/2') return { json: second }
      if (path.endsWith('/summary')) return { json: makeSummary() }
    })
    return { first, second }
  }

  it('switches between statements and links to the export', async () => {
    setupTwo()
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByText(/select a statement above/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /bank_b_checking\.csv/ }))
    expect(await screen.findByText('SECOND FILE ROW')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /download categorized csv/i })).toHaveAttribute(
      'href',
      '/api/statements/2/export',
    )

    await user.click(screen.getByRole('button', { name: /bank_a_card\.csv/ }))
    expect(await screen.findByText('FIRST FILE ROW')).toBeInTheDocument()
    expect(screen.queryByText('SECOND FILE ROW')).not.toBeInTheDocument()
  })

  it('shows an error when the statement cannot be loaded', async () => {
    installFetch((_method, path) => {
      if (path === '/api/categories') return { json: CATEGORIES }
      if (path === '/api/statements') {
        return { json: [listItem(makeDetail([makeTransaction()]))] }
      }
      if (path === '/api/statements/1') return { status: 404, json: { detail: 'Statement 1 not found' } }
      if (path === '/api/statements/1/summary') return { status: 404, json: { detail: 'Statement 1 not found' } }
    })
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: /bank_a_card\.csv/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Statement 1 not found')
  })

  it('says so when the server cannot be reached', async () => {
    installFetch(() => undefined) // every request fails like a network error
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/cannot reach the server/i)
  })
})
