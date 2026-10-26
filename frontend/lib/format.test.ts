import { describe, expect, it } from "vitest";
import { formatDate, formatMoney, formatPercent, formatSigned, plural } from "./format";

describe("formatMoney", () => {
  it("groups thousands and always shows two decimals", () => {
    expect(formatMoney(45000)).toBe("45,000.00");
    expect(formatMoney(0)).toBe("0.00");
    expect(formatMoney(1234567.5)).toBe("1,234,567.50");
  });
});

describe("formatSigned", () => {
  it("states the direction in text, not only in colour", () => {
    expect(formatSigned(45000)).toBe("+45,000.00");
    expect(formatSigned(-6500)).toBe("−6,500.00"); // a real minus sign, not a hyphen
  });

  it("does not sign zero", () => {
    expect(formatSigned(0)).toBe("0.00");
  });
});

describe("formatDate", () => {
  it("formats an ISO date as day month year", () => {
    expect(formatDate("2026-10-01")).toBe("01 Oct 2026");
    expect(formatDate("2026-01-31")).toBe("31 Jan 2026");
  });

  it("never shifts the day with the viewer's timezone", () => {
    const original = process.env.TZ;
    try {
      for (const tz of ["Pacific/Honolulu", "Asia/Karachi", "Pacific/Kiritimati"]) {
        process.env.TZ = tz;
        expect(formatDate("2026-10-01")).toBe("01 Oct 2026");
      }
    } finally {
      if (original === undefined) delete process.env.TZ;
      else process.env.TZ = original;
    }
  });
});

describe("formatPercent and plural", () => {
  it("rounds confidence to a whole percent", () => {
    expect(formatPercent(0.9)).toBe("90%");
    expect(formatPercent(0)).toBe("0%");
    expect(formatPercent(0.2)).toBe("20%");
  });

  it("pluralises", () => {
    expect(plural(1, "row")).toBe("1 row");
    expect(plural(6, "row")).toBe("6 rows");
    expect(plural(2, "similar row")).toBe("2 similar rows");
    expect(plural(2, "person", "people")).toBe("2 people");
  });
});
