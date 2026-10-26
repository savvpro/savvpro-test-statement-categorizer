export const qk = {
  accounts: () => ["accounts"] as const,
  account: (id: string) => ["accounts", id] as const,
  statements: () => ["statements"] as const,
  statement: (id: string) => ["statements", id] as const,
  transactions: (filters?: object) => ["transactions", filters ?? {}] as const,
  transaction: (id: string) => ["transactions", id] as const,
  reviewQueue: () => ["review"] as const,
  categories: () => ["categories"] as const,
  rules: () => ["rules"] as const,
  dashboard: () => ["dashboard"] as const,
  reports: (year: number) => ["reports", year] as const,
};
