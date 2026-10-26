import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { categories, statement } from "../test/fixtures";
import { TransactionTable } from "./TransactionTable";

function setup() {
  const onSave = vi.fn().mockResolvedValue(undefined);
  render(
    <TransactionTable
      transactions={statement.transactions}
      categories={categories}
      currency="USD"
      savingId={null}
      onSave={onSave}
    />,
  );
  return onSave;
}

const chip = (name: RegExp) => screen.getByRole("button", { name });

function shown(descriptions: string[]) {
  for (const t of statement.transactions) {
    const el = screen.queryByText(t.description);
    if (descriptions.includes(t.description)) expect(el).toBeInTheDocument();
    else expect(el).not.toBeInTheDocument();
  }
}

describe("TransactionTable", () => {
  it("shows every transaction by default, with counts on the chips", () => {
    setup();
    shown(statement.transactions.map((t) => t.description));
    expect(chip(/^All/)).toHaveAttribute("aria-pressed", "true");
    expect(chip(/^Needs review/)).toHaveTextContent("2");
  });

  it("filters with chips", async () => {
    const user = userEvent.setup();
    setup();

    await user.click(chip(/^Needs review/));
    shown(["SQ *JOES CAFE #123", "ACME CREDIT"]);

    await user.click(chip(/^Excluded/));
    shown(["PAYMENT THANK YOU"]);

    await user.click(chip(/^Corrected/));
    shown(["AMZN Mktp US*2K4"]);

    await user.click(chip(/^Categorized/));
    shown(["ADOBE *CREATIVE CLOUD", "ADOBE *CREATIVE CLOUD REFUND", "DELTA AIR LINES"]);

    await user.click(chip(/^Flagged/));
    shown(["SQ *JOES CAFE #123", "ADOBE *CREATIVE CLOUD REFUND", "DELTA AIR LINES", "ACME CREDIT"]);
  });

  it("filters by search text", async () => {
    const user = userEvent.setup();
    setup();
    await user.type(screen.getByLabelText("Search"), "delta");
    shown(["DELTA AIR LINES"]);

    await user.clear(screen.getByLabelText("Search"));
    await user.type(screen.getByLabelText("Search"), "zzzz");
    expect(screen.getByText("No transactions match the current filter.")).toBeInTheDocument();
  });

  it("renders flag pills, badges and confidence", () => {
    setup();
    expect(screen.getByText("Possible duplicate")).toBeInTheDocument();
    expect(screen.getByText("Foreign currency")).toBeInTheDocument();
    expect(screen.getByText("Refund")).toBeInTheDocument();
    expect(screen.getByText("Large amount")).toBeInTheDocument();
    expect(screen.getByText("Unmatched refund")).toBeInTheDocument();
    expect(screen.getByText("Ambiguous merchant")).toBeInTheDocument();
    expect(screen.getByText("95%")).toBeInTheDocument();
    expect(screen.getAllByText("Needs review").length).toBeGreaterThan(0);
  });

  it("expands reasons in a details row", async () => {
    const user = userEvent.setup();
    setup();
    expect(screen.queryByText("Charged in CAD")).not.toBeInTheDocument();

    const button = screen.getByRole("button", { name: "Details for DELTA AIR LINES" });
    await user.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Charged in CAD")).toBeInTheDocument();

    await user.click(button);
    expect(screen.queryByText("Charged in CAD")).not.toBeInTheDocument();
  });

  it("lets a corrected row be edited again", async () => {
    const user = userEvent.setup();
    const onSave = setup();
    await user.click(screen.getByRole("button", { name: "Edit category for AMZN Mktp US*2K4" }));

    const select = screen.getByLabelText("Category");
    expect(select).toHaveValue("office_supplies");
    await user.selectOptions(select, "meals");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith("t-0004", "meals", false);
  });

  it("sorts by amount", async () => {
    const user = userEvent.setup();
    setup();
    await user.click(screen.getByRole("button", { name: /^Amount/ }));
    const body = screen.getAllByRole("rowgroup")[1];
    const firstRow = within(body).getAllByRole("row")[0];
    // Lowest signed amount first: the -312.50 flight.
    expect(firstRow).toHaveTextContent("DELTA AIR LINES");
  });
});
