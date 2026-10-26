/** Client-side CSV export of the final (reviewed) categorization. */

export function exportCsv(sourceFilename, rows) {
  const esc = (v) => {
    const s = String(v ?? '')
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const header = 'Date,Description,Amount,Category,Confidence,Needs Review,Notes'
  const lines = rows.map((t) =>
    [
      t.date ?? t.date_raw,
      t.description,
      t.amount.toFixed(2),
      t.category ?? 'Needs Review',
      `${t.band} (${t.confidence.toFixed(2)})`,
      t.needs_review ? 'yes' : 'no',
      [...t.flags, ...t.reasons].join(' | '),
    ]
      .map(esc)
      .join(','),
  )
  const blob = new Blob([header + '\n' + lines.join('\n')], {
    type: 'text/csv;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const base = sourceFilename.replace(/\.csv$/i, '')
  a.href = url
  a.download = `${base}-categorized.csv`
  a.click()
  URL.revokeObjectURL(url)
}
