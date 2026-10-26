import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { makeCurrency, makeSummary, TWO_CURRENCIES } from '../test/fixtures'
import { SummaryPanel } from './SummaryPanel'

describe('SummaryPanel', () => {
  it('shows each currency on its own and never mixes them', () => {
    render(<SummaryPanel summary={TWO_CURRENCIES} status="ready" />)
    const usd = screen.getByRole('region', { name: 'USD' })
    const pkr = screen.getByRole('region', { name: 'PKR' })

    expect(within(usd).getByText('63.99 USD')).toBeInTheDocument()
    expect(within(usd).getByText('59.99 USD')).toBeInTheDocument() // refunds
    expect(within(usd).queryByText(/PKR/)).not.toBeInTheDocument()

    expect(within(pkr).getByText('5,000.00 PKR')).toBeInTheDocument() // fees
    expect(within(pkr).getByText('120.00 PKR')).toBeInTheDocument() // tax already paid
    expect(within(pkr).queryByText(/USD/)).not.toBeInTheDocument()
  })

  it('labels personal, transfers and unreviewed money as outside the totals', () => {
    render(<SummaryPanel summary={TWO_CURRENCIES} status="ready" />)
    const pkr = screen.getByRole('region', { name: 'PKR' })
    expect(within(pkr).getByText('Tax already paid')).toBeInTheDocument()
    expect(within(pkr).getByText('not deductible')).toBeInTheDocument()
    expect(within(pkr).getByText('not spending')).toBeInTheDocument()
    expect(within(pkr).getByText('not in any total')).toBeInTheDocument()
  })

  it('shows In and Out on separate lines with the note on its own line below', () => {
    render(<SummaryPanel summary={TWO_CURRENCIES} status="ready" />)
    const pkr = screen.getByRole('region', { name: 'PKR' })

    for (const [label, tag, incoming, outgoing] of [
      ['Transfers', 'not spending', 'In: 185,000.00 PKR', 'Out: 0.00 PKR'],
      ['Unreviewed', 'not in any total', 'In: 15,000.00 PKR', 'Out: 3,200.00 PKR'],
    ]) {
      const tile = within(pkr).getByText(label).closest('div') as HTMLElement
      const lines = within(tile).getAllByText(/^(In|Out): /)
      expect(lines.map((line) => line.textContent)).toEqual([incoming, outgoing])
      expect(lines[0]).not.toBe(lines[1]) // two elements, so two lines
      const note = within(tile).getByText(tag)
      expect(note.tagName).toBe('P')
      // the note comes after the figures, in its own element
      expect(lines[1].compareDocumentPosition(note) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
      expect(note.textContent).toBe(tag)
    }
  })

  it('dims cards that have no rows, but keeps them on screen', () => {
    render(<SummaryPanel summary={TWO_CURRENCIES} status="ready" />)
    const usd = screen.getByRole('region', { name: 'USD' })
    const tile = (label: string) => within(usd).getByText(label).closest('div') as HTMLElement

    for (const label of ['Fees', 'Income', 'Tax already paid', 'Personal', 'Transfers', 'Unreviewed']) {
      expect(tile(label)).toHaveClass('tile--empty')
    }
    for (const label of ['Total expenses', 'Refunds']) {
      expect(tile(label)).not.toHaveClass('tile--empty')
    }
    // PKR has rows behind these, so they are not dimmed
    const pkr = screen.getByRole('region', { name: 'PKR' })
    for (const label of ['Fees', 'Personal', 'Transfers', 'Unreviewed']) {
      expect(within(pkr).getByText(label).closest('div')).not.toHaveClass('tile--empty')
    }
    expect(within(pkr).getByText('Refunds').closest('div')).toHaveClass('tile--empty')
  })

  it('lists expenses by category inside each currency', () => {
    render(<SummaryPanel summary={TWO_CURRENCIES} status="ready" />)
    const usd = screen.getByRole('table', { name: /expenses by category \(USD\)/i })
    expect(within(usd).getByRole('rowheader', { name: 'Software & Subscriptions' })).toBeInTheDocument()
    const pkr = screen.getByRole('table', { name: /expenses by category \(PKR\)/i })
    expect(within(pkr).getByRole('rowheader', { name: 'Meals' })).toBeInTheDocument()
    expect(within(pkr).queryByText('Software & Subscriptions')).not.toBeInTheDocument()
  })

  it('has loading and empty states', () => {
    const { rerender } = render(<SummaryPanel summary={null} status="loading" />)
    expect(screen.getByRole('status')).toHaveTextContent(/loading summary/i)
    rerender(<SummaryPanel summary={makeSummary()} status="ready" />)
    expect(screen.getByText(/nothing to total yet/i)).toBeInTheDocument()
    rerender(<SummaryPanel summary={makeSummary({ PKR: makeCurrency() })} status="ready" />)
    expect(screen.getByText(/no expenses categorized yet in PKR/i)).toBeInTheDocument()
  })
})
