import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ParseErrorsPanel } from './ParseErrorsPanel'

describe('ParseErrorsPanel', () => {
  it('lists the row, the raw line and the reason', () => {
    render(
      <ParseErrorsPanel
        errors={[{ row_number: 12, raw_line: '2026-09-11,X,-1,PKR,EXTRA', reason: 'expected 4 columns, got 5' }]}
        skippedCount={1}
      />,
    )
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('2026-09-11,X,-1,PKR,EXTRA')).toBeInTheDocument()
    expect(screen.getByText('expected 4 columns, got 5')).toBeInTheDocument()
    expect(screen.getByText(/1 blank line was ignored/)).toBeInTheDocument()
  })

  it('has an empty state', () => {
    render(<ParseErrorsPanel errors={[]} skippedCount={0} />)
    expect(screen.getByText(/every line was read/i)).toBeInTheDocument()
  })
})
