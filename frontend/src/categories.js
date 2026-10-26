// One colour per category. The page header stripe is built from the same list.
export const CATEGORY_COLORS = {
  'Business Income': '#0b8f6a',
  'Software & Subscriptions': '#2347c5',
  'Cloud & Hosting': '#5b3fd1',
  'Internet & Phone': '#0e8c9a',
  'Platform & Payment Fees': '#8e3b8c',
  'Bank Charges': '#c2412d',
  'Office & Equipment': '#c98a12',
  'Travel & Transport': '#e06a1b',
  Meals: '#6e9f18',
  Utilities: '#1f7fbf',
  'Tax Deducted': '#b4233c',
  Transfer: '#5a6b85',
  Personal: '#d6246e',
}

export const colorFor = (name) => CATEGORY_COLORS[name] ?? '#8a94a8'
