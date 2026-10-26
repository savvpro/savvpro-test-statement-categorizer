export const money = (value) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);

const csvCell = (value) => {
  let text = String(value ?? "");
  // Stop spreadsheet apps from running a statement description as a formula.
  if (/^[=+\-@\t\r]/.test(text) && Number.isNaN(Number(text))) text = `'${text}`;
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
};

export function toCsv(transactions) {
  const header = ["Date", "Description", "Amount", "Category", "Type", "Needs review", "Reason"];
  const rows = transactions.map((t) =>
    [t.date, t.description, t.amount, t.category, t.kind, t.needs_review ? "yes" : "no", t.reason].map(csvCell).join(",")
  );
  return [header.join(","), ...rows].join("\n");
}
