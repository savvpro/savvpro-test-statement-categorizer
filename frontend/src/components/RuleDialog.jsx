import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { shortDate, signedMoney } from '../format'
import { Button, CategoryChip, CategorySelect } from './ui'

const MATCH_LABELS = { contains: 'contains', starts_with: 'starts with', exact: 'is exactly' }

export default function RuleDialog({ draft, categories, onClose, onCreated }) {
  const [rule, setRule] = useState({
    pattern: draft.pattern,
    match_type: draft.match_type ?? 'contains',
    category: draft.category,
  })
  const [preview, setPreview] = useState(null)
  const [problem, setProblem] = useState('')
  const [busy, setBusy] = useState(false)
  const firstField = useRef(null)

  useEffect(() => {
    firstField.current?.focus()
    const onKey = (event) => event.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  useEffect(() => {
    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        const result = await api.previewRule(rule)
        if (!cancelled) {
          setPreview(result)
          setProblem('')
        }
      } catch (error) {
        if (!cancelled) {
          setPreview(null)
          setProblem(error.message)
        }
      }
    }, 300)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [rule])

  async function create() {
    setBusy(true)
    try {
      const result = await api.createRule({ ...rule, from_transaction_id: draft.txnId ?? null })
      onCreated(result)
    } catch (error) {
      setProblem(error.message)
    } finally {
      setBusy(false)
    }
  }

  const decided = preview?.affected.filter((a) => a.after.status === 'auto').length ?? 0

  return (
    <div className="fixed inset-0 z-20 flex items-end justify-center bg-ink/40 p-0 sm:items-center sm:p-6" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="rule-title"
        onClick={(event) => event.stopPropagation()}
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-t-2xl bg-white p-6 shadow-xl sm:rounded-2xl"
      >
        <h2 id="rule-title" className="font-display text-2xl font-bold tracking-tight">
          Make a rule
        </h2>
        <p className="mt-1 text-sm text-ink-soft">
          Your rules are checked before the built-in ones. They only change rows that still need review, and every
          statement you upload later.
        </p>

        <div className="mt-5 grid gap-3 sm:grid-cols-[auto_1fr] sm:items-center">
          <label htmlFor="rule-match" className="text-sm font-medium">
            When the description
          </label>
          <div className="flex gap-2">
            <select
              id="rule-match"
              value={rule.match_type}
              onChange={(event) => setRule({ ...rule, match_type: event.target.value })}
              className="rounded-lg border border-line bg-white px-2.5 py-1.5 text-sm"
            >
              {Object.entries(MATCH_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <input
              ref={firstField}
              aria-label="Text to match"
              value={rule.pattern}
              onChange={(event) => setRule({ ...rule, pattern: event.target.value })}
              className="min-w-0 flex-1 rounded-lg border border-line px-3 py-1.5 font-medium uppercase"
            />
          </div>
          <label htmlFor="rule-category" className="text-sm font-medium">
            put it in
          </label>
          <CategorySelect
            id="rule-category"
            categories={categories}
            value={rule.category}
            onChange={(category) => setRule({ ...rule, category })}
          />
        </div>

        {problem && (
          <p role="alert" className="mt-4 rounded-lg bg-rani-soft px-3 py-2 text-sm text-[#9c1450]">
            {problem}
          </p>
        )}

        {preview && (
          <div className="mt-5 space-y-3 text-sm">
            <p>
              {preview.affected.length === 0
                ? 'No rows waiting for review match this rule.'
                : `${preview.affected.length} ${preview.affected.length === 1 ? 'row' : 'rows'} waiting for review ${preview.affected.length === 1 ? 'matches' : 'match'}. ${decided} will be sorted now.`}
              {preview.already_decided > 0 &&
                ` ${preview.already_decided} matching ${preview.already_decided === 1 ? 'row is' : 'rows are'} already sorted and won't change.`}
            </p>

            {preview.affected.length > 0 && (
              <ul className="divide-y divide-line rounded-xl border border-line">
                {preview.affected.map((row) => (
                  <li key={row.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2">
                    <span className="tabular w-24 text-ink-soft">{shortDate(row.date)}</span>
                    <span className="min-w-0 flex-1 truncate font-medium">{row.description}</span>
                    <span className="tabular">{signedMoney(row.amount, row.currency)}</span>
                    {row.after.status === 'auto' ? (
                      <CategoryChip name={row.after.category} />
                    ) : (
                      <span className="w-full text-[#7a5200]">Stays in review: {row.after.reason}</span>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {preview.overlaps.map((overlap) => (
              <p key={overlap.id} className="rounded-lg bg-paper px-3 py-2">
                Overlaps {overlap.source === 'user' ? 'your rule' : 'built-in rule'} <strong>{overlap.id}</strong>{' '}
                {`(${overlap.pattern}, ${overlap.category ?? 'always review'}).`} {overlap.note}
              </p>
            ))}
          </div>
        )}

        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <Button variant="quiet" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={create} disabled={busy || !preview || !rule.category}>
            {busy ? 'Saving…' : 'Create rule'}
          </Button>
        </div>
      </div>
    </div>
  )
}
