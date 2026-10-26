import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DEFAULT_CONFIG } from "../api/client";
import { UploadPanel } from "./UploadPanel";

function setup(props: Partial<React.ComponentProps<typeof UploadPanel>> = {}) {
  const onUpload = vi.fn();
  render(
    <UploadPanel
      onUpload={onUpload}
      loading={false}
      error={null}
      config={DEFAULT_CONFIG}
      {...props}
    />,
  );
  return onUpload;
}

describe("UploadPanel", () => {
  it("submits the chosen file with the default convention", async () => {
    const user = userEvent.setup();
    const onUpload = setup();
    const file = new File(["date,amount"], "march.csv", { type: "text/csv" });

    await user.upload(screen.getByLabelText("Choose file"), file);
    expect(screen.getByText("Selected: march.csv")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Categorize statement" }));

    expect(onUpload).toHaveBeenCalledWith(file, "auto");
  });

  it("passes the selected amount convention", async () => {
    const user = userEvent.setup();
    const onUpload = setup();
    const file = new File(["x"], "march.csv", { type: "text/csv" });

    await user.click(screen.getByText("Advanced"));
    await user.selectOptions(screen.getByLabelText("Amount convention"), "positive_is_spending");
    await user.upload(screen.getByLabelText("Choose file"), file);
    await user.click(screen.getByRole("button", { name: "Categorize statement" }));

    expect(onUpload).toHaveBeenCalledWith(file, "positive_is_spending");
  });

  it("uses the config for accept and the helper text", () => {
    setup({ config: { ...DEFAULT_CONFIG, max_upload_mb: 8, accepted_extensions: [".csv", ".pdf"] } });
    expect(screen.getByLabelText("Choose file")).toHaveAttribute("accept", ".csv,.pdf");
    expect(screen.getByText("CSV, PDF. Up to 8 MB.")).toBeInTheDocument();
  });

  it("shows a friendly error for an unsupported file without uploading", async () => {
    const user = userEvent.setup({ applyAccept: false });
    const onUpload = setup();
    await user.upload(
      screen.getByLabelText("Choose file"),
      new File(["x"], "notes.docx", { type: "application/msword" }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/not a supported file type/);
    await user.click(screen.getByRole("button", { name: "Categorize statement" }));
    expect(onUpload).not.toHaveBeenCalled();
  });

  it("shows an oversized file error", async () => {
    const user = userEvent.setup();
    setup({ config: { ...DEFAULT_CONFIG, max_upload_mb: 1 } });
    const big = new File([new Uint8Array(2 * 1024 * 1024)], "big.csv", { type: "text/csv" });
    await user.upload(screen.getByLabelText("Choose file"), big);
    expect(screen.getByRole("alert")).toHaveTextContent(/limit is 1 MB/);
  });

  it("shows an API error with its title", () => {
    setup({ error: { title: "No transactions found", message: "Nothing to import." } });
    expect(screen.getByRole("alert")).toHaveTextContent("No transactions found. Nothing to import.");
  });

  it("disables the button and shows the wait time after a rate limit", () => {
    setup({ retryUntil: Date.now() + 30_000 });
    expect(screen.getByRole("alert")).toHaveTextContent(/Too many requests, try again in \d+ s/);
    expect(screen.getByRole("button", { name: "Categorize statement" })).toBeDisabled();
  });

  it("re-enables the button once the wait is over", () => {
    setup({ retryUntil: Date.now() - 1000 });
    expect(screen.getByRole("button", { name: "Categorize statement" })).toBeEnabled();
  });

  it("shows a loading state", () => {
    setup({ loading: true });
    expect(screen.getByRole("button", { name: /Categorizing/ })).toBeDisabled();
  });
});
