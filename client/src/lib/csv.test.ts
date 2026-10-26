import { describe, expect, it } from "vitest";
import { parseStatementCsv } from "./csv";

describe("statement CSV parser", () => {
  it("maps flexible headers and preserves uncertainty", () => {
    const result = parseStatementCsv([
      "Posted Date,Merchant,Value,Debit/Credit",
      "2026-01-03,ADOBE CREATIVE CLOUD,$59.99,Debit",
      "2026-01-04,JOES CAFE 9921,$18.75,Debit",
    ].join("\n"));
    expect(result.transactions[0].category).toBe("Software");
    expect(result.transactions[1].status).toBe("needs_review");
    expect(result.transactions[1].ruleLabel).toContain("No specific merchant rule");
  });

  it("flags missing required headers without throwing away the file", () => {
    const result = parseStatementCsv("Date,Description\n2026-01-01,Adobe");
    expect(result.transactions).toHaveLength(0);
    expect(result.issues[0]).toContain("Missing required column: amount");
  });
});
