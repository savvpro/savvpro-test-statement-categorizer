import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { api, ApiError } from "../api";
import { UploadForm } from "./UploadForm";

describe("statement import", () => {
  it("requires a file before contacting the server", async () => {
    const request = vi.spyOn(api, "import");
    render(<UploadForm onImported={vi.fn()} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Import statement" }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Choose a statement");
    expect(request).not.toHaveBeenCalled();
  });

  it("sends the explicitly selected date, amount, and currency conventions", async () => {
    const request = vi
      .spyOn(api, "import")
      .mockResolvedValue({ id: "new-statement", reused: false });
    const imported = vi.fn().mockResolvedValue(undefined);
    render(<UploadForm onImported={imported} />);
    const user = userEvent.setup();
    await user.upload(
      screen.getByLabelText("Statement CSV file"),
      new File(["Date,Description,Amount"], "fake.csv", { type: "text/csv" }),
    );
    await user.selectOptions(
      screen.getByLabelText("Amount format"),
      "card_signed",
    );
    await user.selectOptions(
      screen.getByLabelText("Date format"),
      "month_first",
    );
    await user.selectOptions(screen.getByLabelText("Currency"), "PKR");
    await user.click(screen.getByRole("button", { name: "Import statement" }));
    expect(request.mock.calls[0][0].get("amount_mode")).toBe("card_signed");
    expect(request.mock.calls[0][0].get("date_format")).toBe("month_first");
    expect(request.mock.calls[0][0].get("currency")).toBe("PKR");
    expect(imported).toHaveBeenCalledWith("new-statement", false);
  });

  it("shows row errors and preserves the chosen file after rejection", async () => {
    vi.spyOn(api, "import").mockRejectedValue(
      new ApiError("Nothing was imported.", 422, [
        { row: 3, message: "Invalid amount." },
      ]),
    );
    render(<UploadForm onImported={vi.fn()} />);
    await userEvent.upload(
      screen.getByLabelText("Statement CSV file"),
      new File(["bad"], "fake.csv", { type: "text/csv" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Import statement" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Row 3: Invalid amount.",
    );
    expect(screen.getByText("fake.csv")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Import statement" }),
    ).toBeEnabled();
  });

  it("loads the sample through the same real import contract", async () => {
    vi.spyOn(api, "sample").mockResolvedValue(
      new File(["demo"], "designer-bank.csv"),
    );
    const request = vi
      .spyOn(api, "import")
      .mockResolvedValue({ id: "existing", reused: true });
    const imported = vi.fn().mockResolvedValue(undefined);
    render(<UploadForm onImported={imported} />);
    await userEvent.selectOptions(screen.getByLabelText("Currency"), "GBP");
    await userEvent.click(screen.getByRole("button", { name: /Try a sample/ }));
    expect(request.mock.calls[0][0].get("currency")).toBe("USD");
    expect(imported).toHaveBeenCalledWith("existing", true);
  });
});
