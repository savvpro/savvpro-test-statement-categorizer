const twoPlaces = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export function money(value, currency) {
  const symbol = currency === 'USD' ? '$' : 'Rs '
  return `${symbol}${twoPlaces.format(Math.abs(Number(value)))}`
}

export function signedMoney(value, currency) {
  const n = Number(value)
  const sign = n > 0 ? '+' : n < 0 ? '−' : ''
  return `${sign}${money(n, currency)}`
}

export function shortDate(iso) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}
