// Fails when a text/background colour pair drops below WCAG AA (4.5:1 text, 3:1 UI components).
// Reads the colour tokens from the :root block in src/app/globals.css.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const css = readFileSync(fileURLToPath(new URL("../src/app/globals.css", import.meta.url)), "utf8");
const root = css.match(/:root\s*\{([^}]*)\}/)?.[1] ?? "";
const t = {};
for (const m of root.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)) t[m[1]] = m[2];

const lum = (hex) => {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) =>
    c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const ratio = (a, b) => {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

// [foreground token, background token, minimum ratio, what it is]
const pairs = [
  ["ink", "paper", 4.5, "body text"],
  ["ink", "row", 4.5, "text on rows"],
  ["ink", "attention-fill", 4.5, "text on attention fill"],
  ["ledger", "paper", 4.5, "links and accent text"],
  ["ledger", "row", 4.5, "links on white"],
  ["muted", "paper", 4.5, "secondary text"],
  ["muted", "row", 4.5, "secondary text on white"],
  ["muted", "attention-fill", 4.5, "secondary text on attention fill"],
  ["attention", "paper", 4.5, "attention text"],
  ["attention", "row", 4.5, "attention text on white"],
  ["attention", "attention-fill", 4.5, "attention text on its fill"],
  ["error", "paper", 4.5, "error text"],
  ["error", "row", 4.5, "error text on white"],
  ["row", "ledger", 4.5, "white text on Confirm button"],
  ["row", "ink", 4.5, "white text on toast"],
  ["ledger", "row", 3, "focus ring and selected edge vs white"],
  ["ledger", "paper", 3, "focus ring vs paper"],
  ["muted", "row", 3, "input and quick-pick borders vs white"],
];

let failed = 0;
for (const [fg, bg, min, what] of pairs) {
  if (!t[fg] || !t[bg]) {
    console.error(`missing token: ${fg} or ${bg}`);
    failed++;
    continue;
  }
  const r = ratio(t[fg], t[bg]);
  const ok = r >= min;
  if (!ok) failed++;
  console.log(`${ok ? "ok  " : "FAIL"} ${r.toFixed(2).padStart(5)} (min ${min}) ${fg} on ${bg}: ${what}`);
}
if (failed) {
  console.error(`${failed} contrast pair(s) failed`);
  process.exit(1);
}
