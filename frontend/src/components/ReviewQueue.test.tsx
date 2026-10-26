import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { categories, statement } from "../test/fixtures";
import { ReviewQueue } from "./ReviewQueue";

const css = readFileSync("src/styles.css", "utf8");

function setup(transactions = statement.transactions) {
  const onSave = vi.fn().mockResolvedValue(undefined);
  render(
    <ReviewQueue
      transactions={transactions}
      categories={categories}
      currency="USD"
      savingId={null}
      onSave={onSave}
    />,
  );
  return onSave;
}

describe("ReviewQueue", () => {
  it("lists only rows that need review", () => {
    setup();
    expect(screen.getByRole("heading", { name: "Needs review (2)" })).toBeInTheDocument();
    expect(screen.getByRole("article", { name: /SQ \*JOES CAFE/ })).toBeInTheDocument();
    expect(screen.getByRole("article", { name: /ACME CREDIT/ })).toBeInTheDocument();
    expect(screen.queryByRole("article", { name: /ADOBE/ })).not.toBeInTheDocument();
  });

  it("groups categories by kind and leaves out the review bucket", () => {
    setup();
    const item = within(screen.getByRole("article", { name: /JOES CAFE/ }));
    const select = item.getByLabelText("Category");
    expect(within(select).getByRole("group", { name: "Expenses" })).toBeInTheDocument();
    expect(within(select).getByRole("group", { name: "Non-spending (excluded)" })).toBeInTheDocument();
    expect(within(select).queryByRole("option", { name: "Needs Review" })).not.toBeInTheDocument();
  });

  it("keeps Save disabled until a category is picked when there are no suggestions", () => {
    setup();
    const item = within(screen.getByRole("article", { name: /ACME CREDIT/ }));
    expect(item.getByLabelText("Category")).toHaveValue("");
    expect(item.queryByText("Suggested:")).not.toBeInTheDocument();
    expect(item.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("preselects the first suggestion without saving", () => {
    const onSave = setup();
    const item = within(screen.getByRole("article", { name: /JOES CAFE/ }));
    expect(item.getByLabelText("Category")).toHaveValue("meals");
    expect(item.getByText("Suggested:")).toBeInTheDocument();
    expect(item.getByRole("button", { name: "Meals", pressed: true })).toBeInTheDocument();
    expect(item.getByRole("button", { name: "Office Supplies", pressed: false })).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Needs review (2)" })).toBeInTheDocument();
  });

  it("sets the dropdown from a suggestion chip and saves that category", async () => {
    const user = userEvent.setup();
    const onSave = setup();
    const item = within(screen.getByRole("article", { name: /JOES CAFE/ }));

    await user.click(item.getByRole("button", { name: "Office Supplies" }));
    expect(item.getByLabelText("Category")).toHaveValue("office_supplies");
    expect(onSave).not.toHaveBeenCalled();

    await user.click(item.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith("t-0002", "office_supplies", false);
  });

  it("saves with apply_to_similar", async () => {
    const user = userEvent.setup();
    const onSave = setup();
    const item = within(screen.getByRole("article", { name: /JOES CAFE/ }));

    await user.selectOptions(item.getByLabelText("Category"), "meals");
    await user.click(item.getByLabelText("Apply to similar transactions"));
    await user.click(item.getByRole("button", { name: "Save" }));

    expect(onSave).toHaveBeenCalledWith("t-0002", "meals", true);
  });

  it("saves without apply_to_similar by default", async () => {
    const user = userEvent.setup();
    const onSave = setup();
    const item = within(screen.getByRole("article", { name: /ACME CREDIT/ }));

    await user.selectOptions(item.getByLabelText("Category"), "income");
    await user.click(item.getByRole("button", { name: "Save" }));

    expect(onSave).toHaveBeenCalledWith("t-0007", "income", false);
  });

  it("shows an empty state when nothing needs review", () => {
    setup(statement.transactions.filter((t) => t.status !== "needs_review"));
    expect(screen.getByText(/Nothing needs review/)).toBeInTheDocument();
  });

  it("keeps the text column in its own shrinkable grid track", () => {
    setup();
    const item = screen.getByRole("article", { name: /JOES CAFE/ });
    expect(item.querySelector(".review-info")).not.toBeNull();
    expect(item.querySelector(".correction-form")).not.toBeNull();

    // jsdom does not lay anything out, so guard the CSS that prevents the
    // form's min-content width from squeezing the text column.
    const rule = /\.review-item\s*\{[^}]*\}/.exec(css)?.[0] ?? "";
    expect(rule).toMatch(/grid-template-columns:\s*minmax\(0,\s*1fr\)\s+minmax\(0,\s*24rem\)/);
    expect(/\.review-info\s*\{[^}]*min-width:\s*0/.test(css)).toBe(true);
    expect(/\.review-info\s*\{[^}]*overflow-wrap:\s*anywhere/.test(css)).toBe(true);
  });
});
