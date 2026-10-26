const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export function formatMoney(value) {
  const n = Number(value);
  return Number.isFinite(n) ? money.format(n) : String(value);
}

// Text cells starting with = + - @ can run as formulas in Excel; neutralize them.
function csvCell(value) {
  let s = String(value ?? "");
  if (typeof value === "string" && /^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return `"${s.replace(/"/g, '""')}"`;
}

export function downloadCsv(rows) {
  const header = ["Row", "Date", "Description", "Amount", "Category", "Needs review", "Reason"];
  const lines = rows.map((r) =>
    [r.row, r.date, r.description, Number(r.amount), r.category,
     r.needs_review ? "yes" : "no", r.reason].map(csvCell).join(",")
  );
  const blob = new Blob([[header.map(csvCell).join(","), ...lines].join("\n")],
                        { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "categorized-statement.csv";
  a.click();
  URL.revokeObjectURL(url);
}