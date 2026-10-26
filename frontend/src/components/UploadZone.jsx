import { useRef, useState } from 'react'

export default function UploadZone({ onFile, loading }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  function pick(file) {
    if (file && onFile) onFile(file)
  }

  return (
    <main className="upload-main">
      <div
        className={`dropzone ${dragging ? 'dragging' : ''} ${loading ? 'busy' : ''}`}
        onClick={() => !loading && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          if (!loading) pick(e.dataTransfer.files?.[0])
        }}
        role="button"
        tabIndex={0}
        aria-label="Upload a CSV bank statement"
        onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
      >
        {loading ? (
          <div className="dz-loading">
            <div className="spinner" aria-hidden="true" />
            <p>Reading your statement…</p>
          </div>
        ) : (
          <>
            <div className="dz-icon" aria-hidden="true">📄</div>
            <p className="dz-title">Drop a CSV statement here, or click to browse</p>
            <p className="dz-sub">
              Signed amounts (− = money out) · Debit/Credit columns also supported
            </p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          hidden
          onChange={(e) => {
            pick(e.target.files?.[0])
            e.target.value = ''
          }}
        />
      </div>

      <section className="how-it-works">
        <div className="how-card">
          <h3>1 · Upload</h3>
          <p>Drop in a CSV export of a bank or credit-card statement. Nothing leaves your machine's backend — nothing is stored.</p>
        </div>
        <div className="how-card">
          <h3>2 · Every row gets a decision</h3>
          <p>A rule-based brain assigns a category and a confidence score. Transfers are not spending, refunds are not income.</p>
        </div>
        <div className="how-card">
          <h3>3 · Fix what it's unsure about</h3>
          <p>Rows it cannot place go to Needs Review — one dropdown click fixes them and totals update live. Export the finished CSV.</p>
        </div>
      </section>
    </main>
  )
}
