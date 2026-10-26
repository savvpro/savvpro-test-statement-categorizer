import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SummaryCards } from "../components/SummaryCards";
import { CategoryTotals } from "../components/CategoryTotals";
import { TransactionTable } from "../components/TransactionTable";
import { StatementSummary, CategoryTotal, CategorizedTransaction } from "../types";

const mockSummary: StatementSummary = {
  total_transactions: 10,
  total_income: 5000.0,
  total_expenses: 1250.0,
  total_transfers: 800.0,
  total_refunds: 150.0,
  needs_review_count: 2,
  duplicate_count: 1,
  review_progress_percent: 80.0,
};

const mockTotals: CategoryTotal[] = [
  {
    category: "Software & Subscriptions",
    count: 4,
    total_amount: 450.0,
    percentage_of_expenses: 36.0,
  },
  {
    category: "Needs Review",
    count: 2,
    total_amount: 200.0,
    percentage_of_expenses: 16.0,
  },
];

const mockTransactions: CategorizedTransaction[] = [
  {
    id: "tx_1",
    line_number: 1,
    date: "2024-03-01",
    raw_description: "GITHUB INC 800-826-0428",
    normalized_description: "GITHUB INC",
    amount: 21.0,
    transaction_type: "DEBIT",
    category: "Software & Subscriptions",
    confidence: 0.98,
    reason: "Exact merchant rule: 'GITHUB INC'",
    needs_review: false,
    is_refund: false,
    is_transfer: false,
    is_duplicate: false,
    is_personal_ambiguous: false,
    user_overridden: false,
    currency: "USD",
  },
  {
    id: "tx_2",
    line_number: 2,
    date: "2024-03-05",
    raw_description: "AMAZON.COM BILL",
    normalized_description: "AMAZON.COM",
    amount: 45.0,
    transaction_type: "DEBIT",
    category: "Needs Review",
    confidence: 0.5,
    reason: "Personal vs Business Ambiguity",
    needs_review: true,
    is_refund: false,
    is_transfer: false,
    is_duplicate: false,
    is_personal_ambiguous: true,
    user_overridden: false,
    currency: "USD",
  },
];

describe("SummaryCards Component", () => {
  it("renders gross revenue and deductible expenses correctly", () => {
    render(<SummaryCards summary={mockSummary} onFilterNeedsReview={vi.fn()} />);
    expect(screen.getByText("Gross Revenue / Income")).toBeInTheDocument();
    expect(screen.getByText("$5,000.00")).toBeInTheDocument();
    expect(screen.getByText("$1,250.00")).toBeInTheDocument();
    expect(screen.getByText("2 Rows Need Review")).toBeInTheDocument();
  });
});

describe("CategoryTotals Component", () => {
  it("renders active categories and transaction counts", () => {
    render(
      <CategoryTotals
        totals={mockTotals}
        onSelectCategory={vi.fn()}
        selectedCategory={null}
      />
    );
    expect(screen.getByText("Software & Subscriptions")).toBeInTheDocument();
    expect(screen.getByText("Needs Review")).toBeInTheDocument();
    expect(screen.getByText("$450.00")).toBeInTheDocument();
  });
});

describe("TransactionTable Component", () => {
  it("renders transaction rows, normalized merchants, and badges", () => {
    render(
      <TransactionTable
        transactions={mockTransactions}
        categories={["Software & Subscriptions", "Needs Review", "Travel"]}
        onCategoryChange={vi.fn()}
        activeFilterCategory={null}
        onClearCategoryFilter={vi.fn()}
      />
    );
    expect(screen.getByText("GITHUB INC 800-826-0428")).toBeInTheDocument();
    expect(screen.getByText("AMAZON.COM BILL")).toBeInTheDocument();
    expect(screen.getByText("Personal / Business Check")).toBeInTheDocument();
  });
});
