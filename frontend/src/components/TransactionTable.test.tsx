import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { row } from "../test/fixtures";
import { TransactionTable } from "./TransactionTable";

describe("transaction browsing", () => {
  it("searches merchant names and resets pagination", async () => {
    const rows = Array.from({ length: 10 }, (_, i) => ({
      ...row,
      id: `fake-${i}`,
      description: `SHOP ${i}`,
      source_row: i + 2,
    }));
    render(
      <TransactionTable
        rows={rows}
        filter="all"
        onFilter={vi.fn()}
        onReview={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("SHOP 9")).toBeInTheDocument();
    await userEvent.type(screen.getByRole("searchbox"), "SHOP 1");
    expect(screen.getByText("SHOP 1")).toBeInTheDocument();
    expect(screen.queryByText("SHOP 9")).not.toBeInTheDocument();
    expect(screen.getByText("Page 1 of 1")).toBeInTheDocument();
  });

  it("keeps excluded rows out of the accepted filter", () => {
    const rows = [{ ...row, status: "reviewed" as const, excluded: true }];
    render(
      <TransactionTable
        rows={rows}
        filter="accepted"
        onFilter={vi.fn()}
        onReview={vi.fn()}
      />,
    );
    expect(screen.queryByText(row.description)).not.toBeInTheDocument();
    expect(screen.getByText("No matching transactions")).toBeInTheDocument();
  });
});
