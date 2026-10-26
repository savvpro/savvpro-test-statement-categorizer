import { useRef, useState } from 'react'
import { api } from '../api'
import { Button, Panel, Segmented } from './ui'

const ACCOUNT_OPTIONS = [
  { value: 'business', label: 'Business only' },
  { value: 'mixed', label: 'Business and personal' },
]
const CURRENCY_OPTIONS = [
  { value: 'auto', label: 'Detect' },
  { value: 'PKR', label: 'PKR' },
  { value: 'USD', label: 'USD' },
]
const DATE_OPTIONS = [
  { value: 'auto', label: 'Detect' },
  { value: 'day_first', label: 'Day first' },
  { value: 'month_first', label: 'Month first' },
]

export default function UploadPanel({ meta, onUploaded }) {
  const input = useRef(null)
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [options, setOptions] = useState({ account_type: 'business', currency: 'auto', date_format: 'auto' })

  const set = (key) => (value) => setOptions((current) => ({ ...current, [key]: value }))

  function choose(files) {
    setError('')
    setFile(files?.[0] ?? null)
  }

  async function upload() {
    if (!file) return
    setBusy(true)
    setError('')
    try {
      const statement = await api.upload(file, options)
      setFile(null)
      if (input.current) input.current.value = ''
      onUploaded(statement)
    } catch (problem) {
      setError(problem.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Panel title="Add a statement">
      <label
        htmlFor="statement-file"
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setDragging(false)
          choose(event.dataTransfer.files)
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-7 text-center transition-colors ${
          dragging ? 'border-lapis bg-lapis-soft' : 'border-line hover:border-ink-soft'
        }`}
      >
        <svg viewBox="0 0 48 48" className="mb-2 size-10" aria-hidden="true">
          <rect x="10" y="6" width="28" height="36" rx="4" fill="#fff4d9" stroke="#14213d" strokeWidth="2" />
          <path d="M16 16h16M16 23h16M16 30h10" stroke="#f4a300" strokeWidth="3" strokeLinecap="round" />
        </svg>
        {file ? (
          <span className="font-medium">{file.name}</span>
        ) : (
          <span>
            <span className="font-medium text-lapis">Choose a bank statement</span> or drop it here
          </span>
        )}
        <span className="mt-1 text-sm text-ink-soft">
          CSV or PDF, up to {meta?.max_upload_mb ?? 10} MB.{' '}
          {meta && !meta.ocr_available && 'Scanned PDFs need Tesseract, which is not installed.'}
        </span>
        <input
          ref={input}
          id="statement-file"
          type="file"
          accept=".csv,.pdf,text/csv,application/pdf"
          className="sr-only"
          onChange={(event) => choose(event.target.files)}
        />
      </label>

      <div className="mt-5 space-y-4">
        <Segmented
          label="This account is used for"
          value={options.account_type}
          options={ACCOUNT_OPTIONS}
          onChange={set('account_type')}
        />
        <div className="flex flex-wrap gap-x-6 gap-y-4">
          <Segmented label="Currency" value={options.currency} options={CURRENCY_OPTIONS} onChange={set('currency')} />
          <Segmented label="Dates" value={options.date_format} options={DATE_OPTIONS} onChange={set('date_format')} />
        </div>
      </div>

      {error && (
        <p role="alert" className="mt-4 rounded-lg bg-rani-soft px-3 py-2 text-sm text-[#9c1450]">
          {error}
        </p>
      )}

      <Button className="mt-5 w-full py-2.5" onClick={upload} disabled={!file || busy}>
        {busy ? 'Reading the statement…' : 'Upload and sort'}
      </Button>
    </Panel>
  )
}
