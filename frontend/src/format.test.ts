import { describe, expect, it } from "vitest";
import { DEFAULT_CONFIG } from "./api/client";
import {
  acceptedFormatsLabel,
  checkFile,
  flagLabel,
  formatCurrency,
  formatDate,
  formatPercent,
  savedMessage,
  sourceFormatLabel,
} from "./format";

describe("format helpers", () => {
  it("formats currency with sign and grouping", () => {
    expect(formatCurrency(1234.5, "USD")).toBe("$1,234.50");
    expect(formatCurrency(-12.4, "USD")).toBe("-$12.40");
  });

  it("does not throw on an unknown currency code", () => {
    expect(formatCurrency(5, "??")).toContain("5.00");
  });

  it("formats ISO dates without timezone drift", () => {
    expect(formatDate("2024-03-05")).toBe("Mar 5, 2024");
    expect(formatDate("2024-12-31")).toBe("Dec 31, 2024");
    expect(formatDate("not a date")).toBe("not a date");
  });

  it("formats percentages", () => {
    expect(formatPercent(0.856)).toBe("86%");
    expect(formatPercent(1)).toBe("100%");
    expect(formatPercent(0)).toBe("0%");
  });

  it("labels flags", () => {
    expect(flagLabel("possible_duplicate")).toBe("Possible duplicate");
    expect(flagLabel("refund")).toBe("Refund");
  });

  it("builds the saved message", () => {
    expect(savedMessage(3, true)).toBe("Saved. 3 similar transactions updated.");
    expect(savedMessage(1, true)).toBe("Saved. 1 similar transaction updated.");
    expect(savedMessage(1, false)).toBe("Saved.");
  });

  it("summarizes accepted formats", () => {
    expect(acceptedFormatsLabel([".csv", ".tsv", ".xlsx", ".pdf", ".ofx", ".qfx"])).toBe(
      "CSV, Excel, PDF, OFX",
    );
  });
});

describe("format labels", () => {
  it("maps the default extensions to friendly names", () => {
    expect(acceptedFormatsLabel(DEFAULT_CONFIG.accepted_extensions)).toBe(
      "CSV, Excel, PDF, OFX, ISO 20022 XML, SWIFT MT940",
    );
  });

  it("labels source formats", () => {
    expect(sourceFormatLabel("csv")).toBe("CSV");
    expect(sourceFormatLabel("xlsx")).toBe("Excel");
    expect(sourceFormatLabel("pdf")).toBe("PDF");
    expect(sourceFormatLabel("ofx")).toBe("OFX");
    expect(sourceFormatLabel("camt053")).toBe("ISO 20022 camt.053");
    expect(sourceFormatLabel("mt940")).toBe("SWIFT MT940");
  });
});

describe("checkFile", () => {
  const config = { max_upload_mb: 5, accepted_extensions: [".csv", ".pdf"] };

  it("accepts a valid file", () => {
    expect(checkFile({ name: "a.CSV", size: 100 }, config)).toBeNull();
  });

  it("rejects unsupported extensions", () => {
    expect(checkFile({ name: "a.docx", size: 100 }, config)).toMatch(/not a supported file type/);
  });

  it("rejects oversized and empty files", () => {
    expect(checkFile({ name: "a.csv", size: 6 * 1024 * 1024 }, config)).toMatch(/limit is 5 MB/);
    expect(checkFile({ name: "a.csv", size: 0 }, config)).toMatch(/empty/);
  });
});
