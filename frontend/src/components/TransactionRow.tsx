import { useState } from 'react'
import type { Category, Transaction } from '../api/types'
import { amountTone, confidenceLevel, formatDate, formatMoney } from '../format'

const STATUS_LABELS = { auto: 'Auto', needs_review: 'Needs review', user_confirmed: 'Confirmed' }
const FLAG_LABELS: Record<string, string> = {
  pending: 'Pending',
  possible_duplicate: 'Possible duplicate',
  ambiguous: 'Ambiguous',
  chargeback: 'Chargeback',
}
const KIND_LABELS = { expense: 'Business expenses', income: 'Income', non_operating: 'Not business' }

interface Props {
  txn: Transaction
  categories: Category[]
  labels: Record<string, string>
  onSave: (txn: Transaction, categoryId: string, remember: boolean) => Promise<void>
}

export function TransactionRow({ txn, categories, labels, onSave }: Props) {
  const initial = txn.status === 'needs_review' ? (txn.suggested_category_id ?? '') : txn.category_id
  const [choice, setChoice] = useState(initial)
  const [remember, setRemember] = useState(false)
  const [saving, setSaving] = useState(false)
  const [open, setOpen] = useState(false)
  const level = confidenceLevel(txn.confidence)

  const save = async () => {
    setSaving(true)
    try {
      await onSave(txn, choice, remember)
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <tr className={txn.status === 'needs_review' ? 'row-review' : undefined}>
        <td className="nowrap">{formatDate(txn.date)}</td>
        <td>
          <div>{txn.description_raw}</div>
          <div className="muted small mono">{txn.merchant_key}</div>
          {txn.flags.length > 0 && (
            <div className="flags">
              {txn.flags.map((flag) => (
                <span key={flag} className={`badge flag-${flag}`}>
                  {FLAG_LABELS[flag] ?? flag}
                </span>
              ))}
            </div>
          )}
        </td>
        <td className={`num nowrap amount-${amountTone(txn.amount)}`}>{formatMoney(txn.amount)}</td>
        <td>
          <div className="category-edit">
            <select
              aria-label={`Category for ${txn.description_raw}`}
              value={choice}
              onChange={(e) => setChoice(e.target.value)}
              disabled={saving}
            >
              <option value="" disabled>
                Choose a category…
              </option>
              {(['expense', 'income', 'non_operating'] as const).map((kind) => (
                <optgroup key={kind} label={KIND_LABELS[kind]}>
                  {categories
                    .filter((c) => c.kind === kind)
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.label}
                      </option>
                    ))}
                </optgroup>
              ))}
            </select>
            {txn.status === 'needs_review' && txn.suggested_category_id && (
              <span className="muted small">Suggested: {labels[txn.suggested_category_id]}</span>
            )}
            <label className="small checkbox">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                disabled={saving}
              />
              Remember for this merchant
            </label>
            <button
              type="button"
              className="button button-small"
              onClick={save}
              disabled={saving || choice === ''}
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </td>
        <td>
          <span className={`pill pill-${level}`} title={`Confidence ${Math.round(txn.confidence * 100)}%`}>
            {level === 'med' ? 'medium' : level} {Math.round(txn.confidence * 100)}%
          </span>
        </td>
        <td>
          <span className={`badge status-${txn.status}`}>{STATUS_LABELS[txn.status]}</span>
        </td>
        <td>
          <button
            type="button"
            className="link-button"
            aria-expanded={open}
            onClick={() => setOpen(!open)}
            title={txn.reasons.join('\n')}
          >
            {open ? 'Hide' : 'Why?'}
          </button>
        </td>
      </tr>
      {open && (
        <tr className="reasons-row">
          <td colSpan={7}>
            <ul className="plain-list small">
              {txn.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
              {txn.rule_id && <li className="muted mono">rule: {txn.rule_id}</li>}
            </ul>
          </td>
        </tr>
      )}
    </>
  )
}
