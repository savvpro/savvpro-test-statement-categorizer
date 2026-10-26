import type { StatementDetail } from '../api/types'

const SIGN_LABELS: Record<string, string> = {
  as_is: 'Positive is money in, negative is money out',
  charges_positive: 'Card export with charges as positive numbers (flipped)',
  charges_negative: 'Card export with charges as negative numbers',
  debit_credit_columns: 'Separate debit and credit columns',
  type_column: 'A type column marks debits and credits',
  cr_dr_markers: 'CR / DR markers on amounts',
}
const DATE_LABELS: Record<string, string> = {
  month_first: 'month first (MM/DD)',
  day_first: 'day first (DD/MM)',
  unambiguous: 'unambiguous',
}

export function ImportNotes({ statement }: { statement: StatementDetail }) {
  const format = statement.detected_format
  const issues = statement.warnings.length + statement.parse_errors.length
  return (
    <details className="card notes" open={statement.parse_errors.length > 0}>
      <summary>
        Import notes{' '}
        <span className="muted small">
          {format.file_type.toUpperCase()} · {issues === 0 ? 'no issues' : `${issues} to check`}
        </span>
      </summary>
      <dl className="notes-grid">
        <dt>Format</dt>
        <dd>
          {format.file_type.toUpperCase()}
          {format.encoding && `, ${format.encoding}`}
          {format.delimiter && `, delimiter "${format.delimiter === '\t' ? 'tab' : format.delimiter}"`}
          , header on line {format.header_line}, dates {DATE_LABELS[format.date_order] ?? format.date_order}
        </dd>
        <dt>Columns</dt>
        <dd>
          {Object.entries(format.column_map)
            .map(([field, header]) => `${field} ← "${header}"`)
            .join(', ')}
        </dd>
        <dt>Signs</dt>
        <dd>
          {SIGN_LABELS[format.sign_convention] ?? format.sign_convention}
          <div className="muted small">{format.sign_reason}</div>
        </dd>
      </dl>
      {statement.warnings.length > 0 && (
        <>
          <h3>Warnings</h3>
          <ul className="plain-list">
            {statement.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </>
      )}
      {statement.parse_errors.length > 0 && (
        <>
          <h3>Rows that could not be read</h3>
          <ul className="plain-list">
            {statement.parse_errors.map((e) => (
              <li key={e.line_no}>
                Line {e.line_no}: {e.reason}
              </li>
            ))}
          </ul>
        </>
      )}
    </details>
  )
}
