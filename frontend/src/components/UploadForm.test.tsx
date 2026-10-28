import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { UploadForm, checkFile } from "./UploadForm";

function setup() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <UploadForm />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("checkFile", () => {
  it("rejects wrong extensions and big files", () => {
    expect(checkFile(new File(["x"], "a.pdf"))).toMatch(/CSV, OFX or QFX/);
    const big = new File([new Uint8Array(5 * 1024 * 1024 + 1)], "a.csv");
    expect(checkFile(big)).toMatch(/5 MB/);
    expect(checkFile(new File(["a,b"], "a.csv"))).toBeNull();
  });
});

describe("UploadForm", () => {
  it("shows a focus ring on the drop zone when the hidden input is focused", () => {
    setup();
    const input = screen.getByLabelText(/Drop a CSV or OFX file/);
    expect(input).toHaveClass("peer");
    expect(input.nextElementSibling).toHaveClass("peer-focus-visible:outline-2");
  });

  it("shows a friendly error for an unsupported file", async () => {
    setup();
    const input = screen.getByLabelText(/Drop a CSV or OFX file/) as HTMLInputElement;
    await userEvent.upload(input, new File(["x"], "notes.txt"), { applyAccept: false });
    expect(await screen.findByRole("alert")).toHaveTextContent(/CSV, OFX or QFX/);
  });

  it("posts the file with the chosen account type", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "s1" }), { status: 201, headers: { "Content-Type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);
    setup();
    await userEvent.click(screen.getByLabelText("Credit card"));
    await userEvent.upload(screen.getByLabelText(/Drop a CSV or OFX file/), new File(["a,b\n1,2"], "s.csv"));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/statements");
    expect((init.body as FormData).get("account_type")).toBe("credit_card");
  });

  it("offers the existing statement on a 409", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: 409, detail: "existing-id-1234" }), { status: 409 }),
      ),
    );
    setup();
    await userEvent.upload(screen.getByLabelText(/Drop a CSV or OFX file/), new File(["a,b\n1,2"], "s.csv"));
    expect(await screen.findByText(/already uploaded/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open the existing statement/ })).toHaveAttribute(
      "href",
      "/statements/existing-id-1234",
    );
  });
});
