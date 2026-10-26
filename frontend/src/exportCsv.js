// Builds a CSV of the sorted rows in the browser and downloads it.
const quote = (value) => `"${String(value).replace(/"/g, '""')}"`;

export function downloadCsv(rows) {
  const lines = ["Date,Description,Amount,Category"];
  for (const r of rows) {
    lines.push([r.date, quote(r.description), r.amount.toFixed(2), quote(r.category)].join(","));
  }
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "sorted-statement.csv";
  link.click();
  URL.revokeObjectURL(link.href);
}
