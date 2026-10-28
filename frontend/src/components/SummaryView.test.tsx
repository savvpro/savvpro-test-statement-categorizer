import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ScheduleEForm } from "./SummaryView";
import { categories, statement, summary, tx } from "@/test/fixtures";

describe("ScheduleEForm", () => {
  it("lists lines in form order with totals and pending amounts", () => {
    const pending = [tx({ brain_category: "MORTGAGE_INTEREST", amount_cents: -191244 })];
    render(<ScheduleEForm statement={statement} summary={summary} categories={categories} pendingTxs={pending} />);
    const lines = screen.getAllByRole("row").map((r) => within(r).queryAllByRole("rowheader")[0]?.textContent).filter(Boolean);
    expect(lines).toEqual(["3", "12", "14", "17", "20", "21"]);
    expect(screen.getByText("pending 1,912.44")).toBeInTheDocument();
    expect(screen.getByText("16,650.00")).toBeInTheDocument();
  });

  it("shows the unresolved banner, export link and not-counted section", () => {
    render(<ScheduleEForm statement={statement} summary={summary} categories={categories} pendingTxs={[]} />);
    expect(screen.getByText(/2 rows still need review/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Export CSV" })).toHaveAttribute("href", "/api/v1/statements/s1/export.csv");
    expect(screen.getByText("Not counted on Schedule E")).toBeInTheDocument();
    expect(screen.getByText("Transfer between accounts")).toBeInTheDocument();
  });

  it("shows the finished state when nothing is unresolved", () => {
    const done = { ...summary, unresolved: { count: 0, total_abs_cents: 0 } };
    render(<ScheduleEForm statement={statement} summary={done} categories={categories} pendingTxs={[]} />);
    expect(screen.getByText(/All rows reviewed/)).toBeInTheDocument();
  });
});
