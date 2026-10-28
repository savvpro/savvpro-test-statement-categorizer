import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CategorySelect, rankedCategories } from "./CategorySelect";
import { categories } from "@/test/fixtures";

describe("CategorySelect", () => {
  it("hides income categories for an outflow", () => {
    render(<CategorySelect id="c" categories={categories} direction="outflow" value="" suggested="REPAIRS" onChange={() => {}} />);
    const sel = screen.getByRole("combobox");
    expect(within(sel).queryByText(/Rents received/)).toBeNull();
    expect(within(sel).getByText(/Repairs.*suggested/)).toBeInTheDocument();
  });

  it("hides expense categories for an inflow, but allows them for a refund", () => {
    const { rerender } = render(
      <CategorySelect id="c" categories={categories} direction="inflow" value="" suggested={null} onChange={() => {}} />,
    );
    expect(screen.queryByText(/Repairs/)).toBeNull();
    expect(screen.getByText(/Rents received/)).toBeInTheDocument();
    rerender(<CategorySelect id="c" categories={categories} direction="inflow" isRefund value="" suggested={null} onChange={() => {}} />);
    expect(screen.getByText(/Repairs/)).toBeInTheDocument();
  });

  it("ranks the suggestion first", () => {
    const r = rankedCategories(categories, "outflow", false, "UTILITIES");
    expect(r[0]?.code).toBe("UTILITIES");
  });
});
