import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { DecisionPanel, type Draft } from "./DecisionPanel";
import { Toast } from "./Toast";
import { categories, tx } from "@/test/fixtures";

function Harness({
  onConfirm = vi.fn(),
  undo,
  similarRows,
}: {
  onConfirm?: (d: Draft) => void;
  undo?: () => void;
  similarRows?: ReturnType<typeof tx>[];
}) {
  const t = tx();
  const [draft, setDraft] = useState<Draft>({ category: "REPAIRS", remember: false, similar: false });
  return (
    <>
      <DecisionPanel
        tx={t}
        categories={categories}
        draft={draft}
        onDraft={(p) => setDraft({ ...draft, ...p })}
        onConfirm={() => onConfirm(draft)}
        onSkip={() => {}}
        totalSoFar={120418}
        similarRows={similarRows}
      />
      <Toast toast={undo ? { id: 1, message: "Confirmed.", undo } : null} onDismiss={() => {}} />
    </>
  );
}

describe("DecisionPanel", () => {
  it("explains why we are asking and shows the suggestion", () => {
    render(<Harness />);
    expect(screen.getByText("Why we are asking")).toBeInTheDocument();
    expect(screen.getByText(/may be an improvement/)).toBeInTheDocument();
    expect(screen.getByText("suggested")).toBeInTheDocument();
  });

  it("confirms with remember and apply-to-similar", async () => {
    const onConfirm = vi.fn();
    render(<Harness onConfirm={onConfirm} />);
    await userEvent.click(screen.getByLabelText(/Remember for Home Depot/));
    await userEvent.click(screen.getByLabelText(/Also apply to 2 similar/));
    await userEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect(onConfirm).toHaveBeenCalledWith({ category: "REPAIRS", remember: true, similar: true });
  });

  it("changes the category with a quick pick", async () => {
    const onConfirm = vi.fn();
    render(<Harness onConfirm={onConfirm} />);
    await userEvent.click(screen.getByRole("button", { name: /Utilities/ }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect(onConfirm.mock.calls[0]?.[0].category).toBe("UTILITIES");
  });

  it("lists the similar rows before applying", () => {
    render(
      <Harness
        similarRows={[tx({ id: "a", description: "HOME DEPOT #1", amount_cents: -1500 }), tx({ id: "b", description: "HOME DEPOT #2", amount_cents: -2500 })]}
      />,
    );
    const list = screen.getByRole("list", { name: "Similar rows" });
    expect(list).toHaveTextContent("HOME DEPOT #1");
    expect(list).toHaveTextContent("HOME DEPOT #2");
  });

  it("offers undo in the toast", async () => {
    const undo = vi.fn();
    render(<Harness undo={undo} />);
    await userEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(undo).toHaveBeenCalled();
  });
});
