import { describe, expect, it, vi, afterEach } from "vitest";
import { api, ApiError, money, statusOf } from "./api";
afterEach(() => vi.unstubAllGlobals());
describe("API error handling and presentation", () => {
  it("surfaces backend validation issues", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: "Nothing imported",
            errors: [{ row: 3, field: "date", message: "Invalid date" }],
          }),
          { status: 422 },
        ),
      ),
    );
    try {
      await api("/statements");
      throw Error("Expected failure");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).issues[0].row).toBe(3);
    }
  });
  it("explains network failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("fetch failed")),
    );
    await expect(api("/health")).rejects.toThrow("Cannot reach LedgerLens");
  });
  it("formats backend minor units without aggregating", () => {
    expect(money(-125099, "USD")).toBe("-$1,250.99");
    expect(money(0, "USD")).toBe("$0.00");
  });
  it("duplicate exclusion and pending reviews take precedence", () => {
    expect(
      statusOf({
        duplicate_status: "excluded",
        needs_review: false,
        reviewed: true,
      }),
    ).toBe("Excluded");
    expect(
      statusOf({
        duplicate_status: "pending",
        needs_review: true,
        reviewed: true,
      }),
    ).toBe("Needs review");
    expect(
      statusOf({
        duplicate_status: "none",
        needs_review: false,
        reviewed: true,
      }),
    ).toBe("Reviewed");
  });
});
