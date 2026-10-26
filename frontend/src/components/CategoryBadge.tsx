"use client";

import clsx from "clsx";

const CATEGORY_COLORS: Record<string, string> = {
  "Software & Subscriptions": "bg-purple-100 text-purple-800",
  "Travel & Transport": "bg-sky-100 text-sky-800",
  "Food & Dining": "bg-orange-100 text-orange-800",
  "Office & Supplies": "bg-yellow-100 text-yellow-800",
  "Marketing & Advertising": "bg-pink-100 text-pink-800",
  "Education & Training": "bg-emerald-100 text-emerald-800",
  "Professional Services": "bg-indigo-100 text-indigo-800",
  "Health & Wellness": "bg-green-100 text-green-800",
  "Transfer / Non-Expense": "bg-gray-100 text-gray-600",
  "Needs Review": "bg-red-100 text-red-700",
};

interface CategoryBadgeProps {
  category: string;
  isReview?: boolean;
}

export default function CategoryBadge({ category, isReview }: CategoryBadgeProps) {
  const colorClass =
    CATEGORY_COLORS[category] ??
    (isReview ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-700");

  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        colorClass
      )}
    >
      {isReview && (
        <span className="mr-1">⚠</span>
      )}
      {category}
    </span>
  );
}
