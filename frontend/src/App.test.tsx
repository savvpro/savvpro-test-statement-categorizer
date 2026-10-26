import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { categories, statement } from "./test/fixtures";

function json(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("uploads a statement, shows results, and applies a correction", async () => {
    const user = userEvent.setup();
    const corrected = {
      ...statement,
      transactions: statement.transactions.map((t) =>
        t.id === "t-0002"
          ? { ...t, status: "user_corrected" as const, category_id: "meals", category_name: "Meals", kind: "expense" as const }
          : t,
      ),
    };
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      const path = String(url);
      if (path === "/api/config") return json({ detail: "unavailable" }, 500);
      if (path === "/api/categories") return json(categories);
      if (path === "/api/statements" && init?.method === "POST") return json(statement, 201);
      if (init?.method === "PATCH") return json({ statement: corrected, updated_count: 3 });
      return json({ detail: "not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: "Statement Categorizer" })).toBeInTheDocument();
    expect(screen.getByText(/No statement yet/)).toBeInTheDocument();

    await user.upload(
      screen.getByLabelText("Choose file"),
      new File(["x"], "march.csv", { type: "text/csv" }),
    );
    await user.click(screen.getByRole("button", { name: "Categorize statement" }));

    expect(await screen.findByText("march.csv")).toBeInTheDocument();
    expect(screen.getByText("CSV")).toBeInTheDocument();
    expect(screen.getByText("Amount convention was guessed")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Export CSV" })).toHaveAttribute(
      "href",
      "/api/statements/stmt-1/export.csv",
    );
    expect(screen.getByRole("heading", { name: "Needs review (2)" })).toBeInTheDocument();

    // Wait for categories to load, then fix the cafe row.
    await waitFor(() =>
      expect(
        within(screen.getByRole("article", { name: /JOES CAFE/ })).getByLabelText("Category"),
      ).toBeEnabled(),
    );
    const item = within(screen.getByRole("article", { name: /JOES CAFE/ }));
    await user.selectOptions(item.getByLabelText("Category"), "meals");
    await user.click(item.getByLabelText("Apply to similar transactions"));
    await user.click(item.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Saved. 3 similar transactions updated.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Needs review (1)" })).toBeInTheDocument();
  });

  it("shows a friendly message for an API error", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
        const path = String(url);
        if (path === "/api/statements" && init?.method === "POST") {
          return json({ detail: { code: "pdf_no_text", message: "No text layer." } }, 422);
        }
        return json(path === "/api/categories" ? categories : {});
      }),
    );
    render(<App />);
    await user.upload(
      screen.getByLabelText("Choose file"),
      new File(["x"], "scan.pdf", { type: "application/pdf" }),
    );
    await user.click(screen.getByRole("button", { name: "Categorize statement" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No text found in the PDF");
    expect(alert).toHaveTextContent(/exporting a CSV/);
  });

  it("blocks uploads after a 429 with Retry-After", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
        const path = String(url);
        if (path === "/api/statements" && init?.method === "POST") {
          return json({ detail: { code: "rate_limited", message: "Slow down" } }, 429, {
            "Retry-After": "30",
          });
        }
        return json(path === "/api/categories" ? categories : {});
      }),
    );
    render(<App />);
    await user.upload(
      screen.getByLabelText("Choose file"),
      new File(["x"], "march.csv", { type: "text/csv" }),
    );
    await user.click(screen.getByRole("button", { name: "Categorize statement" }));

    expect(await screen.findByText(/Too many requests, try again in \d+ s/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Categorize statement" })).toBeDisabled();
  });
});
