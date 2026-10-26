import { describe, expect, it } from "vitest";
import { displayDate, money } from "./api";

describe("presentation of exact amounts and dates", () => {
  it("formats negative cents and net credits without truncation", () => {
    expect(money(-1, "USD")).toBe("-$0.01");
    expect(money(123456, "USD")).toBe("$1,234.56");
  });
  it("does not shift statement dates with timezone conversion", () => {
    expect(displayDate("2026-04-02")).toBe("02 Apr 2026");
  });
});
