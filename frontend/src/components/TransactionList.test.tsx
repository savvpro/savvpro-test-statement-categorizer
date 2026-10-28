import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TransactionList } from "./TransactionList";
import { categories, tx } from "@/test/fixtures";

describe("TransactionList", () => {
  const items = [
    tx({ id: "a", description: "HOME DEPOT #4410" }),
    tx({ id: "b", description: "ZELLE FROM MARIA", amount_cents: 185000, direction: "inflow", status: "auto", category: "RENT", reasons: [], flags: [] }),
  ];

  it("renders ledger rows with formatted amounts and a reason for review rows", () => {
    render(<TransactionList items={items} selectedId="a" categories={categories} showCategory onSelect={() => {}} />);
    expect(screen.getByText("−3,412.00")).toBeInTheDocument();
    expect(screen.getByText("+1,850.00")).toBeInTheDocument();
    expect(screen.getByText("Matched a hardware store")).toBeInTheDocument();
    expect(screen.getByText("Needs your review")).toBeInTheDocument();
    expect(screen.getByText("Sorted")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "HOME DEPOT #4410" })).toHaveAttribute("aria-current", "true");
  });

  it("selects a row on click", async () => {
    const onSelect = vi.fn();
    render(<TransactionList items={items} selectedId="a" categories={categories} showCategory onSelect={onSelect} />);
    await userEvent.click(screen.getByRole("button", { name: "ZELLE FROM MARIA" }));
    expect(onSelect).toHaveBeenCalledWith("b");
  });
});
