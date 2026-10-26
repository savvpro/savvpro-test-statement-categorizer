import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { CATEGORIES, makeReviewRow, makeTransaction } from '../test/fixtures'
import { TransactionsTable } from './TransactionsTable'

const rows = [
  makeTransaction({ id: 1, row_number: 1, raw_description: 'GOOD ROW' }),
  makeReviewRow({ id: 2, row_number: 2, raw_description: 'REVIEW ROW', suggested_category: 'Meals' }),
  makeTransaction({
    id: 3,
    row_number: 3,
    raw_description: 'FIXED ROW',
    amount: '1250.50',
    edited_by_user: true,
    kind: 'income',
  }),
]

function renderTable(transactions = rows) {
  render(
    <TransactionsTable
      transactions={transactions}
      categories={CATEGORIES.categories}
      kinds={CATEGORIES.kinds}
      editingId={null}
      saving={false}
      saveError=""
      onEdit={vi.fn()}
      onSave={vi.fn()}
    />,
  )
}

describe('TransactionsTable', () => {
  it('formats amounts for display, coloured by direction', () => {
    renderTable()
    expect(screen.getByText('-59.99').closest('td')).toHaveClass('amount--out')
    expect(screen.getByText('1,250.50').closest('td')).toHaveClass('amount--in')
    expect(screen.getByText('-3,200.00').closest('td')).toHaveClass('amount--out')
  })

  it('shows a dash instead of a confidence number for rows that need review', () => {
    renderTable()
    const review = screen.getByRole('row', { name: /REVIEW ROW/ })
    const cell = within(review).getAllByRole('cell')[6]
    expect(cell).toHaveTextContent('—')
    expect(cell).not.toHaveTextContent('%')
    const hint = within(cell).getByTitle(/no confidence is shown for rows that need review/i)
    expect(hint).toHaveAttribute('title', expect.stringMatching(/rule that flagged the row/))
    // rows that are decided still show their number
    expect(within(screen.getByRole('row', { name: /GOOD ROW/ })).getByText('95%')).toBeInTheDocument()
    expect(within(screen.getByRole('row', { name: /FIXED ROW/ })).getByText('95%')).toBeInTheDocument()
  })

  it('highlights review rows and shows the suggestion', () => {
    renderTable()
    const review = screen.getByRole('row', { name: /REVIEW ROW/ })
    expect(review).toHaveClass('row--review')
    expect(within(review).getByText('Needs review')).toBeInTheDocument()
    expect(within(review).getByText('Suggested: Meals')).toBeInTheDocument()
    expect(screen.getByRole('row', { name: /GOOD ROW/ })).not.toHaveClass('row--review')
  })

  it('filters between All, Needs Review and Fixed by me, with counts', async () => {
    renderTable()
    const user = userEvent.setup()
    expect(screen.getByRole('button', { name: /^All 3$/ })).toHaveAttribute('aria-pressed', 'true')

    await user.click(screen.getByRole('button', { name: /^Needs Review 1$/ }))
    expect(screen.getByText('REVIEW ROW')).toBeInTheDocument()
    expect(screen.queryByText('GOOD ROW')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^Fixed by me 1$/ }))
    expect(screen.getByText('FIXED ROW')).toBeInTheDocument()
    expect(screen.queryByText('REVIEW ROW')).not.toBeInTheDocument()
  })

  it('says so when a filter has no rows, or the file had none', async () => {
    renderTable([makeTransaction()])
    await userEvent.setup().click(screen.getByRole('button', { name: /^Needs Review 0$/ }))
    expect(screen.getByText(/no rows in this view/i)).toBeInTheDocument()
  })

  it('has an empty state for a statement with no readable rows', () => {
    renderTable([])
    expect(screen.getByText(/no transactions could be read/i)).toBeInTheDocument()
  })

  it('labels the action by what it does', () => {
    renderTable()
    expect(screen.getByRole('button', { name: 'Fix row 2' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit row 1' })).toBeInTheDocument()
  })
})
