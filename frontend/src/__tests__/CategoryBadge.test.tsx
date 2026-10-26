import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import CategoryBadge from "@/components/CategoryBadge";

describe("CategoryBadge", () => {
  it("renders the category text", () => {
    render(<CategoryBadge category="Software & Subscriptions" />);
    expect(screen.getByText("Software & Subscriptions")).toBeInTheDocument();
  });

  it("shows warning icon for review items", () => {
    render(<CategoryBadge category="Needs Review" isReview={true} />);
    expect(screen.getByText("⚠")).toBeInTheDocument();
  });

  it("does not show warning icon for normal items", () => {
    render(<CategoryBadge category="Travel & Transport" isReview={false} />);
    expect(screen.queryByText("⚠")).not.toBeInTheDocument();
  });

  it("renders without crashing for unknown category", () => {
    render(<CategoryBadge category="Some Unknown Category" />);
    expect(screen.getByText("Some Unknown Category")).toBeInTheDocument();
  });
});
