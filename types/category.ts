export const CATEGORIES=["Software","Advertising and Marketing","Travel and Transportation","Meals and Coffee","Office Supplies","Internet and Phone","Professional Services","Income","Refund","Transfer","Needs Review"] as const;
export type Category=(typeof CATEGORIES)[number];
