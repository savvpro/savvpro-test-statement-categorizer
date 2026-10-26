const money = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const day = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

/** 45000 -> "45,000.00" */
export function formatMoney(value: number): string {
  return money.format(value);
}

/** Always shows the direction in text, so it never depends on colour alone. */
export function formatSigned(value: number): string {
  if (value === 0) return money.format(0);
  return `${value < 0 ? "−" : "+"}${money.format(Math.abs(value))}`;
}

/** "2026-10-01" -> "01 Oct 2026" (UTC, so the day never shifts with the viewer's timezone) */
export function formatDate(iso: string): string {
  return day.format(new Date(`${iso}T00:00:00Z`));
}

export function formatPercent(fraction: number): string {
  return `${Math.round(fraction * 100)}%`;
}

export function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`;
}
