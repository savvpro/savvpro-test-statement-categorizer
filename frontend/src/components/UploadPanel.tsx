import { useId, useRef, useState, type FormEvent } from 'react'
import { errorMessage, uploadStatement, type StatementDetail } from '../api/client'

interface Props {
  onUploaded: (statement: StatementDetail) => void
}

export function UploadPanel({ onUploaded }: Props) {
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!file) {
      setError('Choose a .csv file first.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const statement = await uploadStatement(file)
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
      onUploaded(statement)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel" aria-labelledby="upload-heading">
      <h2 id="upload-heading">Upload a statement</h2>
      <form className="upload-form" onSubmit={submit}>
        <label htmlFor={inputId}>Statement file (.csv)</label>
        <div className="upload-row">
          <input
            ref={inputRef}
            id={inputId}
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null)
              setError('')
            }}
          />
          <button type="submit" className="primary" disabled={busy}>
            {busy ? 'Uploading…' : 'Upload and categorize'}
          </button>
        </div>
      </form>
      {error && (
        <p role="alert" className="alert">
          {error}
        </p>
      )}
      <div className="formats">
        <p>Supported formats (the header row decides which one is used):</p>
        <ul>
          <li>
            <strong>Card statement:</strong> <code>Date,Description,Amount,Currency</code>. Dates
            as YYYY-MM-DD, negative amount = money out.
          </li>
          <li>
            <strong>Bank account:</strong> <code>Txn Date,Details,Debit,Credit,Balance</code>.
            Dates as DD/MM/YYYY, debit and credit in separate columns.
          </li>
        </ul>
        <p>Up to 5 MB. Use fictional data only.</p>
      </div>
    </section>
  )
}
