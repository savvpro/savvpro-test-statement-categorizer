import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { CATEGORIES, makeReviewRow } from '../test/fixtures'
import { ReviewEditor } from './ReviewEditor'

function renderEditor(overrides = {}, onSave = vi.fn()) {
  render(
    <ReviewEditor
      transaction={makeReviewRow(overrides)}
      categories={CATEGORIES.categories}
      kinds={CATEGORIES.kinds}
      saving={false}
      error=""
      onSave={onSave}
      onCancel={vi.fn()}
    />,
  )
  return onSave
}

describe('ReviewEditor', () => {
  it('disables "Remember" with a tooltip when there is no merchant name', () => {
    renderEditor({ merchant_key: '', raw_description: '12345' })
    const checkbox = screen.getByLabelText(/remember for this merchant/i)
    expect(checkbox).toBeDisabled()
    expect(checkbox).not.toBeChecked()
    expect(screen.getByText(/remember for this merchant/i).closest('label')).toHaveAttribute(
      'title',
      'This description has no merchant name to remember',
    )
    expect(screen.getByText('This description has no merchant name to remember.')).toBeVisible()
  })

  it('enables "Remember" when the row has a merchant name', () => {
    renderEditor()
    expect(screen.getByLabelText(/remember for this merchant/i)).toBeEnabled()
    expect(screen.getByText(/XYZ TRADERS RAWALPINDI/)).toBeInTheDocument()
  })

  it('never sends remember=true for a row without a merchant name', async () => {
    const onSave = renderEditor({ merchant_key: '' })
    const user = userEvent.setup()
    await user.selectOptions(screen.getByLabelText('Category'), 'Meals')
    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect(onSave).toHaveBeenCalledWith({ category: 'Meals', remember: false })
  })

  it('starts on the suggested category and focuses the category field', () => {
    renderEditor({ suggested_category: 'Meals' })
    const select = screen.getByLabelText('Category')
    expect(select).toHaveValue('Meals')
    expect(select).toHaveFocus()
  })

  it('can be completed with the keyboard alone', async () => {
    const onSave = renderEditor({ suggested_category: 'Travel' })
    const user = userEvent.setup()
    // focus starts on Category; Tab goes Kind -> Remember -> Save
    await user.tab()
    expect(screen.getByLabelText(/kind/i)).toHaveFocus()
    await user.tab()
    await user.keyboard(' ') // tick "Remember for this merchant"
    await user.tab()
    expect(screen.getByRole('button', { name: 'Save' })).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(onSave).toHaveBeenCalledWith({ category: 'Travel', remember: true })
  })
})
