const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

/** 123456 -> "$1,234.56". Sign is kept: -500 -> "-$5.00". */
export function formatCents(cents: number): string {
  return usd.format(cents / 100);
}

/** "2026-01-03" -> "Jan 3, 2026" without timezone drift. */
export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}
