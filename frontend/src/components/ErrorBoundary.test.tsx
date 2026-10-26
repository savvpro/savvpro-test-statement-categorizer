import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ErrorBoundary } from './ErrorBoundary'

function Broken(): never {
  throw new Error('render failed')
}

describe('ErrorBoundary', () => {
  it('shows a message with a reload button instead of a blank screen when a child crashes', () => {
    const log = vi.spyOn(console, 'error').mockImplementation(() => undefined) // React logs the crash
    render(
      <ErrorBoundary>
        <Broken />
      </ErrorBoundary>,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong — reload the page.')
    expect(screen.getByRole('button', { name: 'Reload page' })).toBeInTheDocument()
    expect(log).toHaveBeenCalledWith(
      'The page crashed while rendering:',
      expect.objectContaining({ message: 'render failed' }),
      expect.any(String),
    )
    log.mockRestore()
  })
})
