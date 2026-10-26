import { describe, expect, it } from "vitest";
import { money, toCsv } from "./format.js";

describe("format", () => {
  it("formats money", () => {
    expect(money(-1234.5)).toBe("-$1,234.50");
  });

  it("quotes commas and quotes in CSV", () => {
    const csv = toCsv([{ date: "2024-03-01", description: 'A, "B"', amount: -1, category: "Travel", kind: "expense", needs_review: false, reason: "x" }]);
    expect(csv.split("\n")[1]).toContain('"A, ""B"""');
  });

  it("neutralises spreadsheet formulas", () => {
    const csv = toCsv([{ date: "2024-03-01", description: "=HYPERLINK(1)", amount: -1, category: "Travel", kind: "expense", needs_review: true, reason: "x" }]);
    expect(csv.split("\n")[1]).toContain("'=HYPERLINK(1)");
  });
});
