import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import type { CorrectionBody, Transaction } from '../api/client'

const NEEDS_REVIEW = 'Needs Review'

interface Props {
  transaction: Transaction
  categories: string[]
  kinds: string[]
  saving: boolean
  error: string
  onSave: (body: CorrectionBody) => void
  onCancel: () => void
}

export function ReviewEditor({
  transaction,
  categories,
  kinds,
  saving,
  error,
  onSave,
  onCancel,
}: Props) {
  const id = useId()
  const categoryRef = useRef<HTMLSelectElement>(null)
  const canRemember = transaction.merchant_key !== ''
  const startCategory =
    transaction.suggested_category ??
    (transaction.category === NEEDS_REVIEW ? '' : transaction.category)
  const [category, setCategory] = useState(startCategory)
  const [kind, setKind] = useState('')
  const [remember, setRemember] = useState(false)

  useEffect(() => categoryRef.current?.focus(), [])

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!category) return
    onSave({
      category,
      ...(kind ? { kind } : {}),
      remember: canRemember && remember,
    })
  }

  return (
    <form className="editor" onSubmit={submit} aria-label={`Fix row ${transaction.row_number}`}>
      <div className="field">
        <label htmlFor={`${id}-category`}>Category</label>
        <select
          ref={categoryRef}
          id={`${id}-category`}
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          required
        >
          <option value="">Choose a category…</option>
          {categories
            .filter((name) => name !== NEEDS_REVIEW)
            .map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor={`${id}-kind`}>Kind (optional)</label>
        <select id={`${id}-kind`} value={kind} onChange={(event) => setKind(event.target.value)}>
          <option value="">Automatic</option>
          {kinds.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </div>
      <div className="field field--check">
        <label
          htmlFor={`${id}-remember`}
          title={canRemember ? undefined : 'This description has no merchant name to remember'}
        >
          <input
            id={`${id}-remember`}
            type="checkbox"
            checked={canRemember && remember}
            disabled={!canRemember}
            aria-describedby={`${id}-remember-hint`}
            onChange={(event) => setRemember(event.target.checked)}
          />{' '}
          Remember for this merchant
        </label>
        <p id={`${id}-remember-hint`} className="hint">
          {canRemember
            ? `Rows of “${transaction.merchant_key}” will use this category.`
            : 'This description has no merchant name to remember.'}
        </p>
      </div>
      <div className="editor-actions">
        <button type="submit" className="primary" disabled={!category || saving}>
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button type="button" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
      </div>
      {error && (
        <p role="alert" className="alert editor-error">
          {error}
        </p>
      )}
    </form>
  )
}
