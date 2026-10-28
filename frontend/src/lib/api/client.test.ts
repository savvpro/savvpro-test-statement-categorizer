import { describe, expect, it } from "vitest";
import { toAppError } from "./client";

describe("toAppError", () => {
  it("maps 413 to a size message", () => {
    expect(toAppError({ status: 413 }).message).toMatch(/larger than 5 MB/);
  });
  it("maps 415 to a format message", () => {
    expect(toAppError({ status: 415 }).message).toMatch(/CSV, OFX or QFX/);
  });
  it("maps 422 with row errors", () => {
    const e = toAppError({
      status: 422,
      detail: "Could not read 1 row.",
      errors: [{ row_index: 14, message: "No date." }],
    });
    expect(e.rowErrors).toEqual(["Row 14: No date."]);
    expect(e.message).toMatch(/upload again/);
  });
  it("maps 409 and keeps the existing id", () => {
    const e = toAppError({ status: 409, detail: "existing_id=abc12345-def" });
    expect(e.status).toBe(409);
    expect(e.existingId).toBeTruthy();
  });
  it("falls back for unknown statuses", () => {
    expect(toAppError({ status: 500 }).message).toMatch(/Try again/);
  });
});
