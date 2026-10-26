import { useState } from 'react'

function Pill({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`rounded-full border px-3.5 py-1.5 text-sm transition-colors ${
        active ? 'border-ink bg-ink text-white' : 'border-line bg-white text-ink hover:border-ink-soft'
      }`}
    >
      {children}
    </button>
  )
}

function Details({ title, items, tone }) {
  const [open, setOpen] = useState(tone === 'error')
  if (!items.length) return null
  return (
    <div className="mt-2">
      <button onClick={() => setOpen(!open)} aria-expanded={open} className="text-sm font-medium underline underline-offset-2">
        {title}
      </button>
      {open && (
        <ul className="mt-2 space-y-1.5">
          {items.map((item) => (
            <li
              key={`${item.source_row}-${item.text}`}
              className={`rounded-lg px-3 py-2 text-sm ${tone === 'error' ? 'bg-rani-soft' : 'bg-paper'}`}
            >
              <span className="font-medium">{item.source_row}:</span> {item.reason}
              <div className="mt-0.5 truncate text-ink-soft">{item.text}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function ImportReport({ statement }) {
  if (!statement) return null
  const report = statement.report
  const kind = { csv: 'CSV file', pdf: 'PDF', ocr: 'scanned PDF (read with OCR)' }[statement.source_kind]
  return (
    <div className="rounded-2xl border border-line bg-white px-5 py-4">
      <p>
        <span className="font-medium">{statement.filename}</span>
        <span className="text-ink-soft">
          {' '}is a {statement.currency} {kind} for a {statement.account_type === 'mixed' ? 'business and personal' : 'business'} account.
        </span>{' '}
        The rules sorted <strong>{report.auto}</strong> of {report.rows_imported} rows
        {report.needs_review > 0 && (
          <>
            {' '}and <strong className="text-[#a86f00]">{report.needs_review}</strong> need you
          </>
        )}
        .
      </p>
      {report.warnings.map((warning) => (
        <p key={warning} className="mt-2 rounded-lg bg-marigold-soft px-3 py-2 text-sm">
          {warning}
        </p>
      ))}
      <Details
        tone="error"
        title={`${report.errors.length} ${report.errors.length === 1 ? 'row' : 'rows'} couldn't be read and were not imported`}
        items={report.errors}
      />
      <Details
        title={`${report.skipped.length} balance or information ${report.skipped.length === 1 ? 'line was' : 'lines were'} skipped`}
        items={report.skipped}
      />
    </div>
  )
}

export default function Statements({ statements, selectedId, onSelect, onDelete, onDeleteAll }) {
  if (!statements.length) return null
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Pill active={selectedId === null} onClick={() => onSelect(null)}>
        All statements
      </Pill>
      {statements.map((s) => (
        <span key={s.id} className="inline-flex items-center">
          <Pill active={selectedId === s.id} onClick={() => onSelect(s.id)}>
            {s.filename}
            {s.review_count > 0 && (
              <span className="ml-2 rounded-full bg-marigold px-1.5 text-xs font-semibold text-ink">{s.review_count}</span>
            )}
          </Pill>
          <button
            onClick={() => onDelete(s)}
            className="ml-0.5 rounded-full p-1.5 text-ink-soft hover:bg-white hover:text-brick"
            aria-label={`Delete ${s.filename} and its rows`}
            title="Delete this import"
          >
            <svg viewBox="0 0 16 16" className="size-3.5" aria-hidden="true">
              <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </span>
      ))}
      <button onClick={onDeleteAll} className="ml-auto text-sm text-ink-soft underline underline-offset-2 hover:text-brick">
        Delete all imported data
      </button>
    </div>
  )
}
