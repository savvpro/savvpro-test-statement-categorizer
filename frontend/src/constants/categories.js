// UI helpers for category colors and number formatting.
// Categories come from the backend, so tones are picked by name
// (with a stable hash fallback for any category we don't know).

const TONES = [
  { bg: "#ede9fe", fg: "#6d28d9" }, // violet
  { bg: "#dbeafe", fg: "#1d4ed8" }, // blue
  { bg: "#ffedd5", fg: "#c2410c" }, // orange
  { bg: "#dcfce7", fg: "#15803d" }, // green
  { bg: "#fee2e2", fg: "#b91c1c" }, // red
  { bg: "#e0f2fe", fg: "#0369a1" }, // sky
  { bg: "#fce7f3", fg: "#be185d" }, // pink
  { bg: "#ecfccb", fg: "#4d7c0f" }, // lime
];

const FIXED = {
  income: { bg: "#ccfbf1", fg: "#0f766e" },
  "needs review": { bg: "#fef3c7", fg: "#b45309" },
  refund: { bg: "#cffafe", fg: "#0e7490" },
  refunds: { bg: "#cffafe", fg: "#0e7490" },
};

export function getCategoryTone(name = "") {
  const key = String(name).toLowerCase();
  if (FIXED[key]) return FIXED[key];
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  return TONES[h % TONES.length];
}

export function formatMoney(n) {
  return Number(n || 0).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
