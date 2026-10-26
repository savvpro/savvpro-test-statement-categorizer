export function formatMoney(amount: number): string {
  const sign = amount < 0 ? '-' : amount > 0 ? '+' : ''
  return `${sign}$${Math.abs(amount).toFixed(2)}`
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toFixed(1)} KB`
}

export function titleCaseDescription(desc: string): string {
  const cleaned = desc.replace(/\s+/g, ' ').trim()
  if (cleaned.length <= 28) {
    return cleaned
      .toLowerCase()
      .replace(/\b\w/g, (c) => c.toUpperCase())
      .replace(/\*/g, ' ')
  }
  const first = cleaned.split(/\s+/).slice(0, 4).join(' ')
  return first
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase())
}
