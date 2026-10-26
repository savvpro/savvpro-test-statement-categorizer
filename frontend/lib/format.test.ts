import { describe, expect, it } from "vitest";
import type { Transaction } from "./api";
import { applyFilters, categoryBars, categoryClass, filterRows, formatPkr, formatSignedPkr, isDebit, netAmount } from "./format";

const tx = (id: number, category: string, needs_review: boolean): Transaction => ({
  id, date: "2025-01-01", description: "x", normalized: "X", amount: "-1", balance: null,
  usd_hint: false, category, confidence: 1, reason: "", needs_review, flags: [],
  user_edited: false, refund_of: null,
});

describe("money", () => {
  it("formats PKR with grouping and keeps big decimals exact", () => {
    expect(formatPkr("1173930")).toContain("1,173,930");
    expect(formatPkr("12345678901234567.25")).toContain("12,345,678,901,234,567.25");
  });
  it("detects debits by sign string", () => {
    expect(isDebit("-1840")).toBe(true);
    expect(isDebit("1840")).toBe(false);
  });
});

describe("filterRows", () => {
  const rows = [tx(1, "Food", false), tx(2, "Needs Review", true), tx(3, "Food", true)];
  it("all returns everything", () => expect(filterRows(rows, "all")).toHaveLength(3));
  it("review keeps only needs_review rows", () =>
    expect(filterRows(rows, "review").map((t) => t.id)).toEqual([2, 3]));
  it("category keeps matching rows", () =>
    expect(filterRows(rows, { category: "Food" }).map((t) => t.id)).toEqual([1, 3]));
});

describe("categoryClass", () => {
  it("makes a css-safe class", () => {
    expect(categoryClass("Software & Tools")).toBe("cat-software-tools");
    expect(categoryClass("Rent/Office")).toBe("cat-rent-office");
  });
});

describe("applyFilters", () => {
  const rows = [
    { ...tx(1, "Food", false), description: "Foodpanda order" },
    { ...tx(2, "Needs Review", true), description: "AMZN MKTP" },
    { ...tx(3, "Food", true), description: "KFC", user_edited: true },
  ];
  it("combines tab, category and search", () => {
    expect(applyFilters(rows, "all", "", "")).toHaveLength(3);
    expect(applyFilters(rows, "edited", "", "").map((t) => t.id)).toEqual([3]);
    expect(applyFilters(rows, "review", "Food", "").map((t) => t.id)).toEqual([3]);
    expect(applyFilters(rows, "all", "", "  PANDA ").map((t) => t.id)).toEqual([1]);
    expect(applyFilters(rows, "all", "Food", "amzn")).toEqual([]);
  });
});

describe("netAmount", () => {
  it("subtracts exactly", () => {
    expect(netAmount("1000.10", "250.20")).toBe("749.90");
    expect(netAmount("100", "250.5")).toBe("-150.50");
    expect(netAmount("0", "0")).toBe("0.00");
    expect(netAmount("12345678901234567.25", "0.05")).toBe("12345678901234567.20");
  });
});

describe("formatSignedPkr", () => {
  it("shows a sign for credits and debits", () => {
    expect(formatSignedPkr("1840")).toContain("+");
    expect(formatSignedPkr("-1840")).toMatch(/[-−]/);
  });
});

describe("categoryBars", () => {
  it("sorts by size and scales to the largest", () => {
    const bars = categoryBars([
      { category: "A", count: 1, net: "-50" },
      { category: "B", count: 1, net: "200" },
      { category: "C", count: 1, net: "0" },
    ]);
    expect(bars.map((b) => [b.category, b.pct])).toEqual([["B", 100], ["A", 25], ["C", 0]]);
  });
  it("handles an empty list", () => expect(categoryBars([])).toEqual([]));
});
