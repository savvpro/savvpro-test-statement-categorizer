import { afterEach, describe, expect, it, vi } from "vitest";
import { statement } from "../test/fixtures";
import {
  ApiError,
  DEFAULT_CONFIG,
  correctTransaction,
  exportUrl,
  fetchConfig,
  getStatement,
  uploadStatement,
} from "./client";

function json(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

function mockFetch(factory: () => Response | Promise<Response>) {
  const fn = vi.fn<typeof fetch>(async () => factory());
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("returns parsed JSON on success", async () => {
    const fetchMock = mockFetch(() => json(statement));
    const result = await getStatement("stmt-1");
    expect(result.id).toBe("stmt-1");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/statements/stmt-1");
  });

  it("throws ApiError with a string detail", async () => {
    mockFetch(() => json({ detail: "Statement not found" }, { status: 404 }));
    const err = await getStatement("nope").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).message).toBe("Statement not found");
    expect((err as ApiError).status).toBe(404);
    expect((err as ApiError).code).toBeNull();
  });

  it("throws ApiError with an object detail", async () => {
    mockFetch(() =>
      json({ detail: { code: "empty_file", message: "The file is empty" } }, { status: 422 }),
    );
    const err = await getStatement("x").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).message).toBe("The file is empty");
    expect((err as ApiError).code).toBe("empty_file");
    expect((err as ApiError).status).toBe(422);
  });

  it("reads Retry-After on a 429", async () => {
    mockFetch(() =>
      json(
        { detail: { code: "rate_limited", message: "Slow down" } },
        { status: 429, headers: { "Retry-After": "7", "Content-Type": "application/json" } },
      ),
    );
    const err = (await getStatement("x").catch((e: unknown) => e)) as ApiError;
    expect(err.code).toBe("rate_limited");
    expect(err.retryAfter).toBe(7);
  });

  it("falls back to a generic message for non-JSON errors", async () => {
    mockFetch(() => new Response("boom", { status: 500 }));
    const err = (await getStatement("x").catch((e: unknown) => e)) as ApiError;
    expect(err.message).toContain("500");
  });

  it("wraps network failures in an ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const err = (await getStatement("x").catch((e: unknown) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
  });

  it("uploads the file and convention as multipart form data", async () => {
    const fetchMock = mockFetch(() => json(statement, { status: 201 }));
    const file = new File(["a,b"], "march.csv", { type: "text/csv" });
    await uploadStatement(file, "positive_is_spending");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/statements");
    expect(init?.method).toBe("POST");
    const body = init?.body as FormData;
    expect((body.get("file") as File).name).toBe("march.csv");
    expect(body.get("amount_convention")).toBe("positive_is_spending");
  });

  it("sends a correction as JSON", async () => {
    const fetchMock = mockFetch(() => json({ statement, updated_count: 2 }));
    await correctTransaction("stmt-1", "t-0002", "meals", true);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/statements/stmt-1/transactions/t-0002");
    expect(init?.method).toBe("PATCH");
    expect(JSON.parse(init?.body as string)).toEqual({
      category_id: "meals",
      apply_to_similar: true,
    });
  });

  it("builds the export URL", () => {
    expect(exportUrl("stmt-1")).toBe("/api/statements/stmt-1/export.csv");
  });
});

describe("fetchConfig", () => {
  it("returns the server config, normalizing extensions", async () => {
    mockFetch(() =>
      json({ max_upload_mb: 10, accepted_extensions: ["CSV", ".pdf"], max_rows: 100, max_pdf_pages: 3 }),
    );
    expect(await fetchConfig()).toEqual({
      max_upload_mb: 10,
      accepted_extensions: [".csv", ".pdf"],
      max_rows: 100,
      max_pdf_pages: 3,
    });
  });

  it("falls back to defaults when the request fails", async () => {
    mockFetch(() => json({ detail: "nope" }, { status: 500 }));
    const config = await fetchConfig();
    expect(config).toEqual(DEFAULT_CONFIG);
    expect(config.accepted_extensions).toEqual([
      ".csv", ".tsv", ".txt", ".xlsx", ".ofx", ".qfx", ".pdf", ".xml", ".sta", ".mt940", ".940", ".dat",
    ]);
    expect(config.max_upload_mb).toBe(5);
  });

  it("falls back to defaults when the network is down", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    expect(await fetchConfig()).toEqual(DEFAULT_CONFIG);
  });
});
