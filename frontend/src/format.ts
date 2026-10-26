// Display helpers. Amounts are decimal strings and are formatted as text, so there is
// no floating-point rounding anywhere between the database and the screen.

export type Direction = 'in' | 'out' | 'zero'

/** "-1850.00" -> "-1,850.00". Anything that is not a plain decimal is returned as it is. */
export function formatAmount(amount: string): string {
  const match = /^(-?)(\d+)(\.\d+)?$/.exec(amount)
  if (!match) return amount
  const [, sign, whole, fraction = ''] = match
  return `${sign}${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}${fraction}`
}

export function amountDirection(amount: string): Direction {
  if (/^-?0+(\.0+)?$/.test(amount)) return 'zero'
  return amount.startsWith('-') ? 'out' : 'in'
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** "2026-09-01" -> "1 Sep 2026" (no time zone is involved, it is a calendar date). */
export function formatDate(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso)
  if (!match) return iso
  return `${Number(match[3])} ${MONTHS[Number(match[2]) - 1] ?? match[2]} ${match[1]}`
}

export function formatDateTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`
}

export function plural(count: number, singular: string, pluralForm = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : pluralForm}`
}
