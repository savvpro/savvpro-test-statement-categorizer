# Feature 6: Dashboard & Review Table

## Goal
Build the main dashboard with tax summary cards, category breakdown chart, interactive transaction table with inline editing, confidence badges, filters, and CSV export.

## Dependencies
- Feature 5 (frontend scaffold & upload) must be complete.
- Backend must be running.

---

## Files to Create / Modify

### 1. `frontend/src/components/TaxDashboard.jsx`
**Props:** `summary` (TaxSummary object), `needsReviewCount`

Four summary metric cards in a row:

| Card | Value | Subtitle | Color |
|------|-------|----------|-------|
| Total Expenses | `$X,XXX.XX` | "Gross business outflow" | Default/white |
| Tax Deductible | `$X,XXX.XX` | "Eligible write-offs" | Emerald green |
| Est. Tax Savings | `$X,XXX.XX` | "At 28% effective rate" | Indigo |
| Needs Review | `N items ($X,XXX)` | "Requires your attention" | Amber (or red if > 5 items) |

Additional info row below cards:
- Gross Business Income: `$X,XXX`
- Net Taxable Profit: `$X,XXX`
- Non-Taxable Transfers: `$X,XXX`

Each card uses the `.card` glassmorphism style with a subtle colored left border accent.
Numbers should animate in with a counting-up effect.

### 2. `frontend/src/components/CategoryChart.jsx`
**Props:** `categories` (list of CategorySummary from TaxSummary)

A horizontal bar chart showing spending by category:
- Each bar labeled with category name + dollar amount
- Bar width proportional to gross_amount relative to the largest category
- Bar color from `TAX_CATEGORIES[category].color`
- Show transaction count next to each bar
- Sort by gross_amount descending
- Exclude categories with 0 transactions

Implementation: Pure CSS/HTML bars (no chart library needed). Each bar is a div with:
- `width: ${(amount / maxAmount) * 100}%`
- `background-color: ${categoryColor}`
- `border-radius: 6px`
- Smooth width transition animation

### 3. `frontend/src/components/CategoryFilter.jsx`
**Props:** `categories` (list of category names), `activeFilter`, `onFilterChange`, `needsReviewCount`

Filter pill buttons:
- **All** (default) — shows total count
- **Needs Review** — shows count, pulsing amber dot indicator
- One pill per category (show only categories that have transactions)

Behavior:
- Click a pill to filter the table below
- Active pill is highlighted with indigo background
- "Needs Review" pill shows a subtle pulse animation if count > 0

### 4. `frontend/src/components/TransactionTable.jsx`
**Props:** `transactions`, `categories` (for dropdown), `filter`, `onTransactionUpdate`

The main interactive table:

**Columns:**
| Column | Content |
|--------|---------|
| Date | Formatted date |
| Merchant | `clean_merchant` (with `raw_description` as tooltip on hover) |
| Amount | Formatted `$X.XX` with color: red for outflow, green for inflow/refund, gray for transfer |
| Direction | Small badge: OUTFLOW, INFLOW, REFUND, TRANSFER |
| Category | If `needs_review=true`: dropdown `<select>` to pick category. If verified: text with category color dot |
| Confidence | Color-coded badge: green (≥85%), yellow (50-84%), red (<50%) with percentage text |
| Status | ✅ Auto Verified, ⚠️ Needs Review, 👤 Manually Approved |
| Actions | "Approve" button for needs-review rows (sets status to MANUALLY_APPROVED) |

**Features:**
- Click column header to sort (ascending/descending toggle)
- Rows with `needs_review=true` have a subtle amber left-border highlight
- Hover row: slight background lighten
- Smooth row transitions when filter changes
- Show `decision_rule` and `review_reason` as expandable detail (click row to expand)

**Inline Editing:**
- When user changes category dropdown on a "Needs Review" row:
  1. Update the transaction's `category` locally
  2. Set `needs_review = false`, `status = "MANUALLY_APPROVED"`
  3. Update `deductible_percentage` and `tax_deductible` from categories data
  4. Call `onTransactionUpdate(updatedTransactions)` to trigger recalculation

### 5. `frontend/src/components/TransactionRow.jsx`
**Props:** `transaction`, `categories`, `onUpdate`, `isExpanded`, `onToggleExpand`

Single table row component:
- Main row with all columns from above
- Expandable detail panel showing:
  - **Decision Rule:** `{transaction.decision_rule}`
  - **Review Reason:** `{transaction.review_reason}` (only if needs_review)
  - **Schedule C Line:** `{transaction.schedule_c_line}`
  - **Deductible:** `{deductible_percentage * 100}%` → `$deductible_amount`
  - **Raw Description:** `{transaction.raw_description}` (the original messy bank text)

### 6. `frontend/src/components/ExportButton.jsx`
**Props:** `transactions`

Button that exports all transactions to a downloadable CSV file.

Export columns: `Date, Raw Description, Clean Merchant, Amount, Direction, Category, Tax Deductible, Deductible %, Deductible Amount, Confidence, Status, Schedule C Line, Review Reason`

Implementation:
1. Build CSV string from transactions array
2. Create Blob with type `text/csv`
3. Create temporary download link
4. Trigger click → downloads `categorized_statement.csv`

### 7. Update `frontend/src/App.jsx`
Full application flow:

```
State:
  data (CategorizeResponse | null)
  transactions (mutable copy for editing)
  summary (TaxSummary, recalculated after edits)
  categories (from GET /api/categories)
  filter ("all" | "needs_review" | category name)
  error

On mount: fetch categories from API

On upload complete:
  - Set data, transactions = data.transactions, summary = data.summary
  - Show any parser warnings as dismissible toast

On transaction update (user edits category):
  - Update local transactions array
  - Call recalculateSummary(transactions) → update summary
  - UI updates reactively

Render (when data loaded):
  <header> "Statement Categorizer" + "Upload New" button
  {warnings && <WarningBanner />}
  <TaxDashboard summary={summary} />
  <CategoryChart categories={summary.categories} />
  <CategoryFilter ... />
  <TransactionTable ... />
  <ExportButton transactions={transactions} />
```

---

## Visual Design Notes

- **Dashboard cards**: Use subtle gradient borders, glass-morphism backgrounds, large bold numbers
- **Category chart bars**: Rounded, with smooth width animation on load
- **Table**: Clean, minimal borders. Alternating very subtle row shading. 
- **Needs Review rows**: Amber left border + slightly different background
- **Confidence badges**: Pill-shaped, small, with the percentage: `🟢 97%`, `🟡 65%`, `🔴 25%`
- **Dropdowns**: Styled select elements matching the dark theme
- **Export button**: Secondary style, positioned at bottom-right of table
- **All transitions**: Smooth 200ms ease for hover states, filter changes, row expansions
- **Responsive**: Stack cards vertically on mobile, table scrolls horizontally

---

## Acceptance Criteria

- [x] Dashboard shows 4 summary cards with correct values from sample data
- [x] Category chart renders all categories with proportional bars
- [x] Filter pills work: clicking "Needs Review" shows only flagged rows
- [x] Transaction table shows all columns with correct formatting
- [x] Amount column color-coded (red/green/gray) by direction
- [x] Confidence badges color-coded (green/yellow/red) by threshold
- [x] Clicking a row expands to show decision details
- [x] Category dropdown appears on "Needs Review" rows
- [x] Changing a category triggers recalculation and updates dashboard
- [x] After manual approval, row status changes to ✅ and recalculation fires
- [x] Export CSV button downloads a valid CSV file
- [x] "Upload New" resets back to upload screen
- [x] Parser warnings (if any) display as dismissible banner

## Verification
Run both backend and frontend, upload sample data or click "Try Demo", verify:
1. All 4 dashboard cards show correct numbers
2. Category chart has bars for each category
3. Filter to "Needs Review" → only flagged transactions shown
4. Change category on a flagged row → dashboard recalculates
5. Click export → CSV downloads with correct data

## Git Commit
```bash
git add frontend/src/
git commit -m "feat(frontend): add tax dashboard, category chart, interactive review table with inline editing, and CSV export"
git push origin candidate-sikandarhussain6858
```
