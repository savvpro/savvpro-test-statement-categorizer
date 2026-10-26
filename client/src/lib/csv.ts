import { categorizeRows, type RawRow, type Transaction } from "./categorizer";

export type ParsedStatement = {
  transactions: Transaction[];
  headers: string[];
  mappedColumns: Record<string, string>;
  issues: string[];
};

function headerKey(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]/g, "");
}

function parseLine(line: string) {
  const cells: string[] = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];
    const next = line[index + 1];
    if (character === '"' && quoted && next === '"') {
      cell += '"';
      index += 1;
    } else if (character === '"') {
      quoted = !quoted;
    } else if (character === "," && !quoted) {
      cells.push(cell.trim());
      cell = "";
    } else {
      cell += character;
    }
  }
  cells.push(cell.trim());
  return cells;
}

function parseCsv(input: string) {
  const lines = input.replace(/^\uFEFF/, "").split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (lines.length < 2) throw new Error("Add a header row and at least one transaction.");
  const headers = parseLine(lines[0]);
  const rows: RawRow[] = lines.slice(1).map((line) => {
    const values = parseLine(line);
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
  });
  return { headers, rows };
}

function mapColumns(headers: string[]) {
  const aliases: Record<string, string[]> = {
    date: ["date", "transactiondate", "posteddate", "postingdate"],
    description: ["description", "merchant", "details", "memo", "payee", "transaction"],
    amount: ["amount", "transactionamount", "value"],
    type: ["type", "transactiontype", "debitcredit", "direction"],
  };
  return Object.fromEntries(Object.entries(aliases).flatMap(([canonical, options]) => {
    const match = headers.find((header) => options.includes(headerKey(header)));
    return match ? [[canonical, match]] : [];
  }));
}

export function parseStatementCsv(input: string): ParsedStatement {
  const { headers, rows } = parseCsv(input);
  const mappedColumns = mapColumns(headers);
  const issues: string[] = [];
  for (const required of ["date", "description", "amount"]) {
    if (!mappedColumns[required]) issues.push(`Missing required column: ${required}.`);
  }
  if (issues.length > 0) return { transactions: [], headers, mappedColumns, issues };
  const transactions = categorizeRows(rows, mappedColumns);
  const malformed = transactions.filter((transaction) => transaction.reviewReason?.includes("Missing") || transaction.reviewReason?.includes("not numeric"));
  const duplicates = transactions.filter((transaction) => transaction.reviewReason?.includes("duplicate"));
  if (malformed.length > 0) issues.push(`${malformed.length} row${malformed.length === 1 ? "" : "s"} need a data check.`);
  if (duplicates.length > 0) issues.push(`${duplicates.length} exact duplicate${duplicates.length === 1 ? "" : "s"} routed to review.`);
  return { transactions, headers, mappedColumns, issues };
}

export function exportStatementCsv(transactions: Transaction[], headers: string[]) {
  const outputHeaders = [...headers, "Category", "Status", "Confidence", "Rule", "Review note"];
  const escape = (value: unknown) => {
    const text = value == null ? "" : String(value);
    return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  const lines = transactions.map((transaction) => [
    ...headers.map((header) => transaction.raw[header] ?? ""),
    transaction.category,
    transaction.status,
    transaction.confidence,
    transaction.ruleLabel,
    transaction.reviewReason ?? "",
  ].map(escape).join(","));
  return [outputHeaders.map(escape).join(","), ...lines].join("\n");
}
