import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, getStatement } from "./api/client";
import { describeError } from "./errors";

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubError(status: number, detail: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(JSON.stringify({ detail }), {
          status,
          headers: { "Content-Type": "application/json" },
        }),
    ),
  );
}

describe("describeError", () => {
  it("shows a friendly message for a 500 internal_error", async () => {
    stubError(500, { code: "internal_error", message: "Traceback (most recent call last)" });
    const err = await getStatement("x").catch((e: unknown) => e);
    const friendly = describeError(err);
    expect(friendly.title).toBe("Something went wrong on our side");
    expect(friendly.message).toMatch(/try again/i);
    expect(friendly.message).not.toMatch(/traceback/i);
  });

  it("treats any 5xx as a server fault", () => {
    const friendly = describeError(new ApiError("Request failed (HTTP 502)", 502));
    expect(friendly.title).toBe("Something went wrong on our side");
  });

  it("maps a 404 transaction_not_found", async () => {
    stubError(404, { code: "transaction_not_found", message: "No transaction t-0099" });
    const err = await getStatement("x").catch((e: unknown) => e);
    expect(describeError(err)).toEqual({
      title: "Transaction not found",
      message: "No transaction t-0099",
    });
  });

  it("maps the other known codes", () => {
    expect(describeError(new ApiError("m", 404, "not_found")).title).toBe("Not found");
    expect(describeError(new ApiError("m", 405, "method_not_allowed")).title).toBe(
      "Action not allowed",
    );
    expect(describeError(new ApiError("Bad field", 422, "invalid_request"))).toEqual({
      title: "Invalid request",
      message: "Bad field",
    });
  });

  it("falls back to a generic title for unknown codes and plain errors", () => {
    expect(describeError(new ApiError("Odd", 400, "mystery")).title).toBe("Something went wrong");
    expect(describeError(new Error("boom"))).toEqual({
      title: "Something went wrong",
      message: "boom",
    });
  });
});
