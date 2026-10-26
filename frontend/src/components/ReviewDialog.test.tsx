import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { api, ApiError } from "../api";
import { row } from "../test/fixtures";
import { ReviewDialog } from "./ReviewDialog";

describe("transaction review", () => {
  it("saves a human choice with the expected version and original amount direction", async () => {
    const request = vi
      .spyOn(api, "review")
      .mockResolvedValue({ ...row, category: "Meals", kind: "expense" });
    const close = vi.fn();
    render(
      <ReviewDialog
        transaction={row}
        onClose={close}
        onSaved={vi.fn().mockResolvedValue(undefined)}
      />,
    );
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Category"), "Meals");
    await user.type(screen.getByLabelText(/Review note/), "Client meeting.");
    await user.click(screen.getByRole("button", { name: "Save decision" }));
    expect(request).toHaveBeenCalledWith(row.id, {
      category: "Meals",
      kind: "expense",
      excluded: false,
      note: "Client meeting.",
      expected_version: 1,
    });
    expect(close).toHaveBeenCalled();
  });

  it("selects a refund movement for a positive expense-category row", async () => {
    render(
      <ReviewDialog
        transaction={{ ...row, amount_minor: 1000 }}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    await userEvent.selectOptions(
      screen.getByLabelText("Category"),
      "Software",
    );
    expect(screen.getByLabelText("Money movement")).toHaveValue("refund");
  });

  it("keeps the dialog open on a concurrent-edit conflict", async () => {
    vi.spyOn(api, "review").mockRejectedValue(
      new ApiError("This transaction changed in another tab.", 409),
    );
    const close = vi.fn();
    render(
      <ReviewDialog transaction={row} onClose={close} onSaved={vi.fn()} />,
    );
    await userEvent.selectOptions(screen.getByLabelText("Category"), "Meals");
    await userEvent.click(
      screen.getByRole("button", { name: "Save decision" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "changed in another tab",
    );
    expect(close).not.toHaveBeenCalled();
  });
});
