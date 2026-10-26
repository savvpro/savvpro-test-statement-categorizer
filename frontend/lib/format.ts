const formatters = new Map<string, Intl.NumberFormat>();

function currencyFormatter(currency: string): Intl.NumberFormat {
  const code = (currency || "USD").toUpperCase();
  let f = formatters.get(code);
  if (!f) {
    try {
      f = new Intl.NumberFormat("en-US", { style: "currency", currency: code });
    } catch {
      f = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    formatters.set(code, f);
  }
  return f;
}

/** Positive magnitude, e.g. "$1,204.56". */
export function formatMoney(value: number, currency = "USD"): string {
  return currencyFormatter(currency).format(Math.abs(Number.isFinite(value) ? value : 0));
}

/** Signed amount: "+$30.00" for money in, "-$12.50" for money out. */
export function formatSignedMoney(value: number, currency = "USD"): string {
  const sign = value > 0 ? "+" : value < 0 ? "\u2212" : "";
  return `${sign}${formatMoney(value, currency)}`;
}

export function formatPercent(value: number): string {
  const v = Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0;
  return `${Math.round(v * 100)}%`;
}

const dateFmt = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });
const dateTimeFmt = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

/** ISO YYYY-MM-DD shown as "May 3, 2026" without timezone drift. */
export function formatDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso ?? "");
  if (!m) return iso || "-";
  return dateFmt.format(new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso || "-" : dateTimeFmt.format(d);
}
