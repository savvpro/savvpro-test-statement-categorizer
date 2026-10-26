import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { categories, categoryMap, tx } from "../test-fixtures";
import { TransactionTable } from "./TransactionTable";

function setup(onChange = vi.fn()) {
  const rows = [
    tx({ merchant: "SHELL OIL" }),
    tx({
      merchant: "JOES CAFE",
      description: "SQ *JOES CAFE 9921",
      category: null,
      status: "needs_review",
      confidence: 0.68,
      suggestions: ["personal"],
      reasons: ["Only 68% sure - asking instead of guessing."],
      engine_category: null,
    }),
  ];
  render(
    <TransactionTable
      transactions={rows}
      categories={categories}
      categoryMap={categoryMap}
      busy={false}
      remember
      onRememberChange={() => {}}
      onChange={onChange}
    />,
  );
  return { rows, onChange };
}

describe("TransactionTable", () => {
  it("opens on the review queue when something needs review", () => {
    setup();
    expect(screen.getByRole("tab", { name: /Needs review/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByText("JOES CAFE")).toBeInTheDocument();
    expect(screen.queryByText("SHELL OIL")).not.toBeInTheDocument();
  });

  it("accepts a suggestion with one click", async () => {
    const { rows, onChange } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Personal (not deductible)" }));
    expect(onChange).toHaveBeenCalledWith(rows[1], "personal");
  });

  it("lets the user pick any category from the dropdown", async () => {
    const { rows, onChange } = setup();
    await userEvent.selectOptions(screen.getByLabelText("Category for JOES CAFE"), "fuel");
    expect(onChange).toHaveBeenCalledWith(rows[1], "fuel");
  });

  it("shows why a decision was made", async () => {
    setup();
    await userEvent.click(screen.getByRole("tab", { name: /All/ }));
    const row = screen.getByText("SHELL OIL").closest("tr")!;
    await userEvent.click(within(row).getByRole("button", { name: /Auto · 92%/ }));
    expect(screen.getByText("Recognised: SHELL.")).toBeInTheDocument();
  });
});
