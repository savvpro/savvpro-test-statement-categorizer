import { useRef, useState } from 'react'
import type { DragEvent } from 'react'
import type { AccountType } from '../api/types'
import type { UploadOptions } from '../api/client'
import { SAMPLES } from '../format'

type ChargesChoice = 'auto' | 'yes' | 'no'
const CHARGES: Record<ChargesChoice, boolean | null> = { auto: null, yes: true, no: false }

interface Props {
  busy: boolean
  duplicateOf: number | null
  onUpload: (file: File, options: UploadOptions) => void
  onSample: (name: string, accountType: AccountType) => void
  onOpenExisting: (id: number) => void
}

export function UploadPanel({ busy, duplicateOf, onUpload, onSample, onOpenExisting }: Props) {
  const [accountType, setAccountType] = useState<AccountType>('checking')
  const [charges, setCharges] = useState<ChargesChoice>('auto')
  const [dragging, setDragging] = useState(false)
  const input = useRef<HTMLInputElement>(null)

  const submit = (file: File | undefined) => {
    if (file) onUpload(file, { accountType, chargesPositive: CHARGES[charges] })
  }

  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    setDragging(false)
    if (!busy) submit(event.dataTransfer.files[0])
  }

  return (
    <section className="card upload" aria-labelledby="upload-title">
      <h2 id="upload-title">Upload a statement</h2>

      <div className="upload-options">
        <label>
          Account type
          <select
            value={accountType}
            onChange={(e) => setAccountType(e.target.value as AccountType)}
            disabled={busy}
          >
            <option value="checking">Checking</option>
            <option value="credit_card">Credit card</option>
          </select>
        </label>
        <label>
          Advanced: charges shown as positive?
          <select
            value={charges}
            onChange={(e) => setCharges(e.target.value as ChargesChoice)}
            disabled={busy}
          >
            <option value="auto">Auto</option>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
        </label>
      </div>

      <div
        className={`dropzone${dragging ? ' dragging' : ''}`}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        {busy ? (
          <p className="muted" aria-live="polite">
            <span className="spinner" aria-hidden="true" /> Reading and categorizing…
          </p>
        ) : (
          <>
            <p>Drag a .csv or .xlsx file here (max 5 MB)</p>
            <button type="button" className="button" onClick={() => input.current?.click()}>
              Choose file
            </button>
          </>
        )}
        <input
          ref={input}
          type="file"
          accept=".csv,.xlsx"
          hidden
          data-testid="file-input"
          onChange={(e) => {
            submit(e.target.files?.[0])
            e.target.value = ''
          }}
        />
      </div>

      {duplicateOf != null && (
        <div className="banner banner-info" role="status">
          <span>This file was already uploaded.</span>
          <button type="button" className="link-button" onClick={() => onOpenExisting(duplicateOf)}>
            Open existing statement
          </button>
        </div>
      )}

      <div className="samples">
        <span className="muted">Try a sample:</span>
        {SAMPLES.map((sample) => (
          <button
            key={sample.name}
            type="button"
            className="button button-ghost"
            disabled={busy}
            onClick={() => onSample(sample.name, sample.accountType)}
          >
            {sample.label}
          </button>
        ))}
      </div>
    </section>
  )
}
