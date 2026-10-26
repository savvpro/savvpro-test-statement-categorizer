import { categoryMap, tx } from "../test-fixtures";
import { countByFilter, filterTransactions } from "./filters";
import { formatCents, formatDate, formatPercent } from "./format";

describe("format", () => {
  it("formats cents as dollars, keeping the sign", () => {
    expect(formatCents(123456)).toBe("$1,234.56");
    expect(formatCents(-500)).toBe("-$5.00");
    expect(formatCents(0)).toBe("$0.00");
  });

  it("formats ISO dates without timezone drift", () => {
    expect(formatDate("2026-01-03")).toBe("Jan 3, 2026");
    expect(formatDate("not-a-date")).toBe("not-a-date");
  });

  it("formats confidence as a percentage", () => {
    expect(formatPercent(0.916)).toBe("92%");
  });
});

describe("filters", () => {
  const rows = [
    tx({ category: "fuel" }),
    tx({ category: null, status: "needs_review", merchant: "JOES CAFE", description: "SQ *JOES CAFE" }),
    tx({ category: "platform_income", amount_cents: 61233, merchant: "UBER USA" }),
    tx({ category: "personal", merchant: "KROGER", description: "KROGER #12" }),
    tx({ category: "transfer", merchant: "TRANSFER TO SAVINGS" }),
  ];

  it("counts rows per tab", () => {
    expect(countByFilter(rows, categoryMap)).toEqual({
      review: 1,
      all: 5,
      income: 1,
      expense: 1,
      personal: 1,
      transfer: 1,
    });
  });

  it("filters by tab", () => {
    expect(filterTransactions(rows, "review", "", categoryMap).map((t) => t.merchant)).toEqual([
      "JOES CAFE",
    ]);
    expect(filterTransactions(rows, "income", "", categoryMap)).toHaveLength(1);
    expect(filterTransactions(rows, "all", "", categoryMap)).toHaveLength(5);
  });

  it("searches merchant, raw description and category label", () => {
    expect(filterTransactions(rows, "all", "kroger", categoryMap)).toHaveLength(1);
    expect(filterTransactions(rows, "all", "sq *joes", categoryMap)).toHaveLength(1);
    expect(filterTransactions(rows, "all", "fuel & ev", categoryMap)).toHaveLength(1);
  });
});
