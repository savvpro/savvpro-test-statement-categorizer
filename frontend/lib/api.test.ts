import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, exportUrl, fetchSampleFile, fixTransaction, uploadStatement } from "./api";

function respond(status: number, body: unknown, asJson = true): Response {
  return new Response(asJson ? JSON.stringify(body) : String(body), { status });
}

function mockFetch(response: Response | Error) {
  const fn = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(async () => {
    if (response instanceof Error) throw response;
    return response;
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

const csv = () => new File(["Date,Description,Amount\n"], "s.csv", { type: "text/csv" });

describe("uploadStatement", () => {
  it("posts the file as multipart form data", async () => {
    const fetchMock = mockFetch(respond(201, { id: "abc" }));
    const result = await uploadStatement(csv(), false);

    expect(result).toEqual({ id: "abc" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/api\/statements$/);
    expect(init?.method).toBe("POST");
    expect(init?.body).toBeInstanceOf(FormData);
    expect((init?.body as FormData).get("file")).toBeInstanceOf(File);
  });

  it("tells the backend when purchases are positive", async () => {
    const fetchMock = mockFetch(respond(201, {}));
    await uploadStatement(csv(), true);
    expect(fetchMock.mock.calls[0][0]).toMatch(/\?purchases_positive=true$/);
  });

  it("surfaces the backend's own message", async () => {
    mockFetch(respond(400, { detail: "Could not find the columns." }));
    await expect(uploadStatement(csv(), false)).rejects.toThrow("Could not find the columns.");
  });

  it("reads the first message of a validation error list", async () => {
    mockFetch(respond(422, { detail: [{ msg: "Field required" }] }));
    await expect(uploadStatement(csv(), false)).rejects.toThrow("Field required");
  });

  it("falls back to the status code when the error body is not JSON", async () => {
    mockFetch(respond(502, "<html>Bad gateway</html>", false));
    await expect(uploadStatement(csv(), false)).rejects.toThrow("HTTP 502");
  });

  it("explains a network failure instead of showing 'Failed to fetch'", async () => {
    mockFetch(new TypeError("Failed to fetch"));
    const promise = uploadStatement(csv(), false);
    await expect(promise).rejects.toBeInstanceOf(ApiError);
    await expect(promise).rejects.toThrow(/Can't reach the server/);
  });
});

describe("fixTransaction", () => {
  it("sends the category as a JSON PATCH", async () => {
    const fetchMock = mockFetch(respond(200, { statement: {}, updated_ids: ["x"] }));
    const result = await fixTransaction("s1", "t1", "Fuel");

    expect(result.updated_ids).toEqual(["x"]);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/api\/statements\/s1\/transactions\/t1$/);
    expect(init?.method).toBe("PATCH");
    expect(JSON.parse(init?.body as string)).toEqual({ category: "Fuel" });
  });

  it("surfaces a 404 message", async () => {
    mockFetch(respond(404, { detail: "Statement not found." }));
    await expect(fixTransaction("s1", "t1", "Fuel")).rejects.toThrow("Statement not found.");
  });
});

describe("helpers", () => {
  it("builds the export link", () => {
    expect(exportUrl("abc")).toMatch(/\/api\/statements\/abc\/export\.csv$/);
  });

  it("fetches the sample as a CSV file", async () => {
    mockFetch(new Response("Date,Description\n", { status: 200 }));
    const file = await fetchSampleFile();
    expect(file.name).toBe("driver_statement.csv");
    expect(file.type).toBe("text/csv");
  });
});
