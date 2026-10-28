const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const plain = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const MINUS = "−";

/** Cents to "$1,234.50"; negatives use a true minus sign. */
export function money(cents: number): string {
  const s = usd.format(Math.abs(cents) / 100);
  return cents < 0 ? `${MINUS}${s}` : s;
}
/** Signed amount without currency sign for list columns. */
export function amount(cents: number): string {
  const s = plain.format(Math.abs(cents) / 100);
  if (cents < 0) return `${MINUS}${s}`;
  return cents > 0 ? `+${s}` : s;
}
export function plainAmount(cents: number): string {
  const s = plain.format(Math.abs(cents) / 100);
  return cents < 0 ? `${MINUS}${s}` : s;
}
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/** "2026-03-04" to "Mar 4" (parsed by hand: no timezone drift). */
export function shortDate(iso: string): string {
  const [, m, d] = iso.split("-");
  return `${MONTHS[Number(m) - 1] ?? ""} ${Number(d)}`;
}
export function period(start: string | null, end: string | null): string {
  if (!start || !end) return "";
  return `${shortDate(start)} to ${shortDate(end)}, ${end.slice(0, 4)}`;
}
export function confidenceWord(c: number): "High" | "Medium" | "Low" {
  return c >= 0.85 ? "High" : c >= 0.6 ? "Medium" : "Low";
}
