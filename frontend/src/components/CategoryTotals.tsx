import React from "react";
import type { CategoryTotal } from "../types";
import { PieChart, Tag } from "lucide-react";

interface CategoryTotalsProps {
  totals: CategoryTotal[];
  onSelectCategory: (category: string) => void;
  selectedCategory: string | null;
}

export const CategoryTotals: React.FC<CategoryTotalsProps> = ({
  totals,
  onSelectCategory,
  selectedCategory,
}) => {
  const activeTotals = totals.filter((t) => t.count > 0);

  return (
    <div className="category-totals-card">
      <div className="card-title-row">
        <div className="title-left">
          <PieChart size={18} className="title-icon" />
          <h3>Tax Category Breakdown</h3>
        </div>
        <span className="badge-count">{activeTotals.length} Active Categories</span>
      </div>

      <div className="category-list">
        {activeTotals.map((item) => {
          const isSelected = selectedCategory === item.category;
          const isNeedsReview = item.category === "Needs Review";

          return (
            <div
              key={item.category}
              className={`category-row ${isSelected ? "selected" : ""} ${
                isNeedsReview ? "needs-review-row" : ""
              }`}
              onClick={() =>
                onSelectCategory(isSelected ? "" : item.category)
              }
            >
              <div className="category-info">
                <div className="category-name-wrap">
                  <Tag size={13} className="cat-icon" />
                  <span className="cat-name">{item.category}</span>
                  {isNeedsReview && (
                    <span className="badge-warning">Action Required</span>
                  )}
                </div>
                <div className="category-stats">
                  <span className="cat-count">{item.count} {item.count === 1 ? "txn" : "txns"}</span>
                  <span className="cat-amount">
                    ${item.total_amount.toLocaleString("en-US", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </span>
                </div>
              </div>

              {/* Expense percentage bar */}
              {item.percentage_of_expenses > 0 && (
                <div className="category-bar-wrapper">
                  <div
                    className="category-bar-fill"
                    style={{ width: `${Math.min(item.percentage_of_expenses, 100)}%` }}
                  />
                  <span className="cat-pct">{item.percentage_of_expenses}% of exp</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
