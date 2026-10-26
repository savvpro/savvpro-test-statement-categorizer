import { useRef, useState } from 'react'
import { Icon } from './Icon'

interface UploadProps {
  busy: boolean
  onUpload: (file: File) => Promise<void>
  onSample: () => Promise<void>
}

export function Upload({ busy, onUpload, onSample }: UploadProps) {
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  return (
    <section className="upload-panel" aria-labelledby="upload-title">
      <div
        className={`drop-area ${dragging ? 'dragging' : ''}`}
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setDragging(false)
          if (!busy && event.dataTransfer.files[0])
            void onUpload(event.dataTransfer.files[0])
        }}
      >
        <span className="upload-icon">
          <Icon name="upload" size={23} />
        </span>
        <div className="upload-copy">
          <h2 id="upload-title">Import a PKR statement</h2>
          <p>Drop a CSV here to categorize and review its transactions.</p>
          <p className="upload-limits">
            PKR statements · CSV only · up to 1 MiB / 5,000 rows
          </p>
        </div>
        <input
          ref={input}
          className="visually-hidden"
          id="statement-file"
          type="file"
          tabIndex={-1}
          accept=".csv,text/csv"
          aria-label="Upload CSV statement"
          disabled={busy}
          onChange={(event) => {
            const file = event.target.files?.[0]
            event.target.value = ''
            if (file) void onUpload(file)
          }}
        />
        <div className="upload-actions">
          <button
            className="button primary"
            disabled={busy}
            onClick={() => input.current?.click()}
          >
            <Icon name="upload" size={16} />
            {busy ? 'Please wait...' : 'Upload statement'}
          </button>
          <button
            className="text-button"
            disabled={busy}
            onClick={() => void onSample()}
          >
            Try fictional sample data
          </button>
        </div>
      </div>
      <details className="format-help">
        <summary>Supported CSV formats</summary>
        <div>
          <p>
            Use <code>Date,Description,Amount</code> with negative amounts for
            money out and positive amounts for money in. Or use{' '}
            <code>Date,Description,Debit,Credit</code> with nonnegative amounts,
            one side per row.
          </p>
          <p>
            Dates: YYYY-MM-DD, DD/MM/YYYY, or DD.MM.YYYY. Decimal point, up to
            two decimal places, no thousands separators. UTF-8 with or without
            BOM. Currency is assumed PKR when absent; an explicit currency must
            be PKR. Type can identify Refund, Internal Transfer, or Client
            Payment.
          </p>
          <p>
            Common aliases include Booking Date, Details, Money Out and Money
            In. Invalid rows reject the whole import. Duplicate-looking entries
            are kept for review.
          </p>
          <a href="/developer-signed.csv" download>
            Signed amount sample
          </a>
          <span> · </span>
          <a href="/developer-debit-credit.csv" download>
            Debit / credit sample
          </a>
        </div>
      </details>
    </section>
  )
}
