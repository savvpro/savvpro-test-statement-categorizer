import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import { UploadPanel } from "./UploadPanel";

test("rejects a non-CSV selection with an actionable error", async () => {
  const user = userEvent.setup({ applyAccept: false });
  const onUpload = vi.fn();
  render(<UploadPanel onUpload={onUpload} busy={false} onDemo={vi.fn()} />);
  await user.upload(
    screen.getByLabelText("Choose CSV statement"),
    new File(["pdf"], "statement.pdf", { type: "application/pdf" }),
  );
  expect(screen.getByRole("alert")).toHaveTextContent("CSV");
  expect(onUpload).not.toHaveBeenCalled();
});

test("requires explicit import and passes the selected parsing options", async () => {
  const user = userEvent.setup();
  const onUpload = vi.fn();
  render(<UploadPanel onUpload={onUpload} busy={false} onDemo={vi.fn()} />);
  const file = new File(
    ["date,description,amount\n2026-10-01,ADOBE,-10"],
    "sample.csv",
    { type: "text/csv" },
  );
  await user.upload(screen.getByLabelText("Choose CSV statement"), file);
  expect(onUpload).not.toHaveBeenCalled();
  await user.selectOptions(screen.getByLabelText("Date format"), "DMY");
  await user.selectOptions(screen.getByLabelText("Currency if missing"), "PKR");
  await user.click(screen.getByRole("button", { name: "Import statement" }));
  expect(onUpload).toHaveBeenCalledWith(file, {
    date_format: "DMY",
    currency: "PKR",
    amount_convention: "negative_expense",
  });
});
