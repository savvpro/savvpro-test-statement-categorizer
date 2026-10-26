export const REVIEW = "Needs Review";

const gbp = new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" });
export const money = (value) => gbp.format(Number(value));
export const percent = (value) => `${(Number(value) * 100).toFixed(1)}%`;

export function totalsByCategory(rows) {
  const totals = new Map();
  for (const row of rows) {
    const current = totals.get(row.category) || { total: 0, count: 0 };
    totals.set(row.category, { total: current.total + Number(row.amount), count: current.count + 1 });
  }
  return [...totals.entries()].map(([category, t]) => ({ category, ...t }));
}
