const escape = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;

export function exportCsv(rows, filename = "categorized-statement.csv") {
  const header = ["Date", "Description", "Merchant", "Amount", "Category", "Confidence", "Flags", "Reason"];
  const lines = rows.map((r) =>
    [r.date, r.description, r.merchant, r.amount, r.category, r.confidence, r.flags.join(" "), r.reasons.join("; ")]
      .map(escape)
      .join(",")
  );
  const url = URL.createObjectURL(new Blob([[header.join(","), ...lines].join("\n")], { type: "text/csv" }));
  const link = Object.assign(document.createElement("a"), { href: url, download: filename });
  link.click();
  URL.revokeObjectURL(url);
}
